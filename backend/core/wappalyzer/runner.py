"""
Wappalyzer Scanner - Exact replica of python-Wappalyzer algorithm.
Reference: https://github.com/chorsley/python-Wappalyzer

Key differences from simple fingerprinting:
1. Detection order matters (most reliable first)
2. Confidence scoring system
3. Multiple detection sources increase confidence
4. Version extraction via regex capture groups
5. Implied technologies (with confidence threshold)
"""
import re
import logging
from typing import Dict, List, Optional, Any, Set, Callable
from dataclasses import dataclass, field
from functools import cmp_to_key

from backend.core.wappalyzer.parser import TechnologyRule, WappalyzerRuleParser

logger = logging.getLogger(__name__)

# Confidence thresholds
CONFIDENCE_THRESHOLD = 30  # Minimum confidence to report a technology
HIGH_CONFIDENCE = 80  # High confidence detection


@dataclass
class ProbeResult:
    """Result from a single probe."""
    url: str
    status_code: int = 0
    headers: Dict[str, str] = field(default_factory=dict)
    cookies: Dict[str, str] = field(default_factory=dict)
    html_content: str = ""
    script_content: str = ""
    scripts: List[str] = field(default_factory=list)  # Script URLs from <script src="">
    inline_scripts: List[str] = field(default_factory=list)  # Inline JavaScript
    meta: Dict[str, str] = field(default_factory=dict)
    dns_records: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


@dataclass
class TechnologyMatch:
    """A matched technology."""
    name: str
    slug: str
    confidence: int
    version: Optional[str] = None
    versions: List[str] = field(default_factory=list)
    categories: List[Dict[str, Any]] = field(default_factory=list)
    icons: Dict[str, Any] = field(default_factory=dict)
    website: Optional[str] = None


@dataclass
class Pattern:
    """Pattern from Wappalyzer rules."""
    string: str
    regex: re.Pattern
    version: Optional[str] = None
    confidence: int = 100


class WappalyzerScanner:
    """
    Wappalyzer-style scanner with strict confidence-based detection.

    Reference: https://github.com/chorsley/python-Wappalyzer
    """

    # Detection type weights (reliability)
    DETECTION_WEIGHTS = {
        'scriptSrc': 100,  # Most reliable - external script URL
        'headers': 100,     # Reliable - server headers
        'meta': 80,        # Medium - meta tags
        'dom': 60,         # Medium-low - DOM structure
        'url': 40,         # Low - URL pattern
        'html': 20,        # Very low - HTML content (needs support from other detections)
        'js': 50,         # Medium - JavaScript variables
        'cookies': 60,    # Medium - Cookies
    }

    def __init__(self, parser: Optional[WappalyzerRuleParser] = None):
        """Initialize the scanner."""
        self.parser = parser or WappalyzerRuleParser()
        self.rules = self.parser.rules
        self.detected_technologies: Dict[str, Dict[str, Dict]] = {}
        self._confidence_regexp = re.compile(r"(.+)\\;confidence:(\d+)")

    def _parse_pattern(self, pattern_str: str) -> Optional[Pattern]:
        """
        Parse Wappalyzer pattern string.
        Format: regex;key:value;key:value (or escaped \;)
        Example: jquery\;version:\1
        """
        import re as re_module

        # Skip empty patterns - they match everything!
        if not pattern_str or not pattern_str.strip():
            return None

        attrs = {'string': '', 'regex': None, 'version': None, 'confidence': 100}

        # Split by escaped semicolon \;
        parts = pattern_str.split(r'\;')

        regex_str = parts[0]
        attrs['string'] = regex_str

        # Skip empty regex strings
        if not regex_str or not regex_str.strip():
            return None

        try:
            attrs['regex'] = re_module.compile(regex_str, re_module.IGNORECASE)
        except re_module.error:
            return None

        for i in range(1, len(parts)):
            expr = parts[i]
            parts_kv = expr.split(':', 1)
            if len(parts_kv) > 1:
                key = parts_kv[0]
                value = parts_kv[1]
                if key == 'confidence':
                    attrs['confidence'] = int(value)
                elif key == 'version':
                    attrs['version'] = value

        return Pattern(**attrs)

    def _parse_pattern_list(self, patterns: Any) -> List[Pattern]:
        """Parse patterns (string, list, or dict values)."""
        result = []

        if isinstance(patterns, str):
            p = self._parse_pattern(patterns)
            if p:
                result.append(p)
        elif isinstance(patterns, list):
            for p in patterns:
                if isinstance(p, str):
                    parsed = self._parse_pattern(p)
                    if parsed:
                        result.append(parsed)
        elif isinstance(patterns, dict):
            for v in patterns.values():
                if isinstance(v, str):
                    parsed = self._parse_pattern(v)
                    if parsed:
                        result.append(parsed)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, str):
                            parsed = self._parse_pattern(item)
                            if parsed:
                                result.append(parsed)

        return result

    def _sort_app_versions(self, version_a: str, version_b: str) -> int:
        """Compare function for sorting versions - ascending by length."""
        return len(version_a) - len(version_b)

    def _cmp_to_key(self, mycmp: Callable[..., Any]):
        """Convert a cmp= function into a key= function."""
        class CmpToKey:
            def __init__(self, obj, *args):
                self.obj = obj

            def __lt__(self, other):
                return mycmp(self.obj, other.obj) < 0

            def __gt__(self, other):
                return mycmp(self.obj, other.obj) > 0

            def __eq__(self, other):
                return mycmp(self.obj, other.obj) == 0

            def __le__(self, other):
                return mycmp(self.obj, other.obj) <= 0

            def __ge__(self, other):
                return mycmp(self.obj, other.obj) >= 0

            def __ne__(self, other):
                return mycmp(self.obj, other.obj) != 0

        return CmpToKey

    async def analyze(self, probe_result: ProbeResult) -> List[TechnologyMatch]:
        """
        Analyze probe results using Wappalyzer algorithm with strict confidence filtering.
        """
        if probe_result.error:
            logger.warning(f"Probe error for {probe_result.url}: {probe_result.error}")
            return []

        self.detected_technologies[probe_result.url] = {}

        # Get scripts and inline scripts
        scripts = list(probe_result.scripts) if probe_result.scripts else []
        if not scripts:
            scripts = self._extract_scripts_from_html(probe_result.html_content)

        inline_scripts = list(probe_result.inline_scripts) if probe_result.inline_scripts else []
        if not inline_scripts:
            inline_scripts = self._extract_inline_scripts(probe_result.html_content)

        meta = probe_result.meta if probe_result.meta else self._extract_meta(probe_result.html_content)

        # Check each technology
        for tech_name, rule in self.rules.items():
            if not rule or not rule.raw_rules:
                continue

            self._has_technology(tech_name, rule, probe_result, scripts, inline_scripts, meta)

        # Get implied technologies
        detected = set(self.detected_technologies[probe_result.url].keys())
        implied = self._get_implied_technologies(detected)
        detected.update(implied)

        # Build results with strict confidence filtering
        results = []
        for name in detected:
            if name in self.detected_technologies[probe_result.url]:
                tech_data = self.detected_technologies[probe_result.url][name]
                confidence_total = sum(tech_data['confidence'].values())
                versions = tech_data.get('versions', [])
                is_html_only = tech_data.get('html_only', False)

                # Strict confidence threshold
                if confidence_total < CONFIDENCE_THRESHOLD:
                    continue

                # HTML-only detection requires higher threshold
                if is_html_only and confidence_total < 60:
                    continue

                rule = self.parser.get_rule(name)

                results.append(TechnologyMatch(
                    name=name,
                    slug=name.lower().replace(' ', '-'),
                    confidence=min(100, confidence_total),
                    version=versions[0] if versions else None,
                    versions=versions,
                    categories=rule.categories if rule else [],
                    icons=rule.icons if rule else {},
                    website=rule.website if rule else None
                ))

        # Sort by confidence (descending)
        results.sort(key=lambda x: -x.confidence)
        return results

    def _has_technology(
        self,
        tech_name: str,
        rule: TechnologyRule,
        probe: ProbeResult,
        scripts: List[str],
        inline_scripts: List[str],
        meta: Dict[str, str]
    ) -> bool:
        """
        Check if technology matches with Wappalyzer algorithm.
        
        Key difference: HTML detection requires other evidence to be considered valid.
        """
        has_tech = False
        has_html_detection = False
        has_reliable_detection = False
        url = probe.url
        html = probe.html_content
        raw = rule.raw_rules

        # 1. scriptSrc patterns (MOST RELIABLE - external scripts)
        scriptsrc_patterns = self._parse_pattern_list(raw.get('scriptSrc'))
        for pattern in scriptsrc_patterns:
            for script in scripts:
                if pattern.regex.search(script):
                    self._set_detected_app(url, tech_name, 'scriptSrc', pattern, script)
                    has_tech = True
                    has_reliable_detection = True

        # 2. headers patterns (RELIABLE)
        headers_data = raw.get('headers', {})
        for header_name, pattern_data in headers_data.items():
            header_value = probe.headers.get(header_name.lower())
            if header_value is not None:
                patterns = self._parse_pattern_list(pattern_data)
                for pattern in patterns:
                    if pattern.regex.search(header_value):
                        self._set_detected_app(url, tech_name, 'headers', pattern, header_value, header_name)
                        has_tech = True
                        has_reliable_detection = True

        # 3. meta patterns (MEDIUM)
        meta_data = raw.get('meta', {})
        for meta_name, pattern_data in meta_data.items():
            meta_value = meta.get(meta_name.lower())
            if meta_value is not None:
                patterns = self._parse_pattern_list(pattern_data)
                for pattern in patterns:
                    if pattern.regex.search(meta_value):
                        self._set_detected_app(url, tech_name, 'meta', pattern, meta_value, meta_name)
                        has_tech = True
                        has_reliable_detection = True

        # 4. url patterns (LOW - but still useful)
        url_patterns = self._parse_pattern_list(raw.get('url'))
        for pattern in url_patterns:
            if pattern.regex.search(url):
                self._set_detected_app(url, tech_name, 'url', pattern, url)

        # 5. DOM patterns (MEDIUM - CSS selectors)
        dom_data = raw.get('dom')
        if dom_data:
            dom_detected = self._check_dom_patterns(url, tech_name, html, dom_data)
            if dom_detected:
                has_tech = True
                has_reliable_detection = True

        # 6. JavaScript variable patterns (js field) - CRITICAL for version detection
        # Format: {"variableName": "regex_pattern"}
        # js detection only works when there are inline scripts to analyze
        js_data = raw.get('js', {})
        if js_data and inline_scripts:
            inline_js = '\n'.join(inline_scripts)
            if isinstance(js_data, dict):
                for var_name, pattern_str in js_data.items():
                    if isinstance(pattern_str, str) and pattern_str.strip():
                        pattern = self._parse_pattern(pattern_str)
                        if pattern and pattern.regex.search(inline_js):
                            self._set_detected_app(url, tech_name, 'js', pattern, inline_js, var_name)
                            has_tech = True
                            has_reliable_detection = True

        # 7. cookies patterns (MEDIUM)
        cookies_data = raw.get('cookies', {})
        for cookie_name, pattern_data in cookies_data.items():
            cookie_value = probe.cookies.get(cookie_name)
            if cookie_value is not None:
                if pattern_data:
                    patterns = self._parse_pattern_list(pattern_data)
                    for pattern in patterns:
                        if pattern.regex.search(cookie_value):
                            self._set_detected_app(url, tech_name, 'cookies', pattern, cookie_value, cookie_name)
                            has_tech = True
                            has_reliable_detection = True
                else:
                    self._set_detected_app(url, tech_name, 'cookies', Pattern(cookie_name, re.compile(''), 100), cookie_value, cookie_name)
                    has_tech = True
                    has_reliable_detection = True

        # 8. HTML patterns (VERY LOW - requires other evidence)
        # HTML detection alone is prone to false positives
        html_patterns = self._parse_pattern_list(raw.get('html'))
        for pattern in html_patterns:
            if pattern.regex.search(html):
                # Only count HTML detection if there's other evidence
                if has_reliable_detection:
                    self._set_detected_app(url, tech_name, 'html', pattern, html)
                    has_html_detection = True
                else:
                    # Apply penalty for HTML-only detection
                    pattern.confidence = 15
                    self._set_detected_app(url, tech_name, 'html', pattern, html)
                    has_html_detection = True

        # If only HTML was detected, mark it
        if has_html_detection and not has_reliable_detection:
            # Apply stricter threshold for HTML-only detections
            detected = self.detected_technologies[url].get(tech_name, {})
            if detected:
                detected['html_only'] = True

        return has_tech

    def _check_dom_patterns(
        self,
        url: str,
        tech_name: str,
        html: str,
        dom_data: Any
    ) -> bool:
        """Check DOM patterns using CSS selectors with selectolax."""
        try:
            from selectolax.parser import HTMLParser
        except ImportError:
            return False

        has_tech = False
        parser = HTMLParser(html)

        if isinstance(dom_data, str):
            try:
                nodes = parser.css(dom_data)
                if nodes:
                    pattern = Pattern(string=dom_data, regex=re.compile(''), confidence=60)
                    self._set_detected_app(url, tech_name, 'dom', pattern, html)
                    has_tech = True
            except Exception:
                pass

        elif isinstance(dom_data, dict):
            for selector, conditions in dom_data.items():
                try:
                    nodes = parser.css(selector)
                    if not nodes:
                        continue

                    if isinstance(conditions, str):
                        pattern = Pattern(string=selector, regex=re.compile(''), confidence=60)
                        self._set_detected_app(url, tech_name, 'dom', pattern, html)
                        has_tech = True

                    elif isinstance(conditions, dict):
                        if conditions.get('exists') is not None:
                            pattern = Pattern(string=selector, regex=re.compile(''), confidence=60)
                            self._set_detected_app(url, tech_name, 'dom', pattern, html)
                            has_tech = True

                        if 'text' in conditions:
                            text_patterns = self._parse_pattern_list(conditions['text'])
                            for node in nodes:
                                node_text = node.text()
                                for pattern in text_patterns:
                                    if pattern.regex.search(node_text):
                                        self._set_detected_app(url, tech_name, 'dom', pattern, node_text)
                                        has_tech = True

                        if 'attributes' in conditions:
                            attrs_conditions = conditions['attributes']
                            if isinstance(attrs_conditions, dict):
                                for attr_name, attr_patterns_data in attrs_conditions.items():
                                    attr_patterns = self._parse_pattern_list(attr_patterns_data)
                                    for node in nodes:
                                        attr_value = node.attributes.get(attr_name, '')
                                        for pattern in attr_patterns:
                                            if pattern.regex.search(attr_value):
                                                self._set_detected_app(url, tech_name, 'dom', pattern, attr_value)
                                                has_tech = True

                except Exception:
                    pass

        return has_tech

    def _set_detected_app(
        self,
        url: str,
        tech_name: str,
        app_type: str,
        pattern: Pattern,
        value: str,
        key: str = ''
    ) -> None:
        """Store detected technology with confidence scoring."""
        if url not in self.detected_technologies:
            self.detected_technologies[url] = {}

        if tech_name not in self.detected_technologies[url]:
            self.detected_technologies[url][tech_name] = {
                'confidence': {},
                'versions': []
            }

        detected = self.detected_technologies[url][tech_name]

        # Apply detection type weight
        base_confidence = self.DETECTION_WEIGHTS.get(app_type, 50)
        pattern_confidence = pattern.confidence
        final_confidence = (base_confidence * pattern_confidence) // 100

        if key:
            key = key + ' '
        match_name = f"{app_type} {key}{pattern.string}"
        detected['confidence'][match_name] = final_confidence

        # Version extraction
        if pattern.version and value:
            try:
                all_matches = pattern.regex.findall(value)
                for matches in all_matches:
                    version = pattern.version

                    if isinstance(matches, str):
                        matches = (matches,)

                    for index, match in enumerate(matches):
                        if not match:
                            continue

                        ternary = re.search(
                            re.compile(r'\\' + str(index + 1) + r'\?([^:]+):(.*)$', re.IGNORECASE),
                            version
                        )
                        if ternary and len(ternary.groups()) == 2:
                            version = version.replace(
                                ternary.group(0),
                                ternary.group(1) if match != '' else ternary.group(2)
                            )

                        version = version.replace('\\' + str(index + 1), match)

                    # Filter out invalid version strings
                    # Must look like a real version number (e.g., 1.2.3, 5.0, 2.1.10)
                    if version and self._is_valid_version(version):
                        detected['versions'].append(version)

                if detected['versions']:
                    detected['versions'] = sorted(
                        detected['versions'],
                        key=self._cmp_to_key(self._sort_app_versions)
                    )
            except Exception:
                pass

    @staticmethod
    def _is_valid_version(version: str) -> bool:
        """Check if version string looks like a real version number."""
        import re as re_module
        # Valid version patterns:
        # - Numeric versions: 1.2.3, 5.0, 2.1.10, 1.0.0-beta, 1.0.0_rc1
        # - Single numbers: 5, 10
        if not version or len(version) > 50:
            return False
        
        # Skip obvious non-version strings
        invalid_patterns = [
            r'^\\', r'\{', r'\}', r'\[', r'\]', r'\(', r'\)',
            r'^\s*$', r'^[\s\.\-]+$',
        ]
        for p in invalid_patterns:
            if re_module.match(p, version):
                return False
        
        # Version must contain at least one digit
        if not re_module.search(r'\d', version):
            return False
        
        # Version should have a reasonable pattern (digit, dot, dash combinations)
        # or be a simple number
        if re_module.match(r'^[\d]+(\.[\d]+)*[-._]?[\w]*$', version, re_module.I):
            return True
        
        return False

    def _get_implied_technologies(self, detected: Set[str]) -> Set[str]:
        """Get implied technologies with confidence threshold."""
        def __get_implied_technologies(technologies: Set[str]) -> Set[str]:
            implied = set()

            for tech in technologies:
                rule = self.parser.get_rule(tech)
                if not rule or not rule.raw_rules:
                    continue

                implies = rule.raw_rules.get('implies')
                if not implies:
                    continue

                if isinstance(implies, str):
                    implies_list = [implies]
                elif isinstance(implies, dict):
                    implies_list = list(implies.keys())
                elif isinstance(implies, list):
                    implies_list = implies
                else:
                    continue

                for implie in implies_list:
                    if 'confidence' not in implie:
                        implied.add(implie)
                    else:
                        try:
                            match = self._confidence_regexp.search(implie)
                            if match:
                                app_name, confidence = match.groups()
                                if int(confidence) >= 50:
                                    implied.add(app_name)
                        except (ValueError, AttributeError, TypeError):
                            pass

            return implied

        implied_technologies = __get_implied_technologies(detected)
        all_implied_technologies: Set[str] = set()

        while not all_implied_technologies.issuperset(implied_technologies):
            all_implied_technologies.update(implied_technologies)
            implied_technologies = __get_implied_technologies(all_implied_technologies)

        return all_implied_technologies

    def _extract_scripts_from_html(self, html: str) -> List[str]:
        """Extract script URLs from HTML."""
        if not html:
            return []

        scripts = []
        pattern = re.compile(r'<script[^>]+src=["\']([^"\']+)["\'][^>]*>', re.IGNORECASE)
        for match in pattern.finditer(html):
            src = match.group(1)
            if src:
                scripts.append(src)

        return scripts

    def _extract_inline_scripts(self, html: str) -> List[str]:
        """Extract inline JavaScript code from HTML."""
        if not html:
            return []

        inline_scripts = []
        pattern = re.compile(r'<script(?![^>]*src)[^>]*>(.*?)</script>', re.DOTALL | re.IGNORECASE)
        for match in pattern.finditer(html):
            content = match.group(1)
            if content and content.strip():
                inline_scripts.append(content)

        return inline_scripts

    def _extract_meta(self, html: str) -> Dict[str, str]:
        """Extract meta tags from HTML."""
        meta = {}

        if not html:
            return meta

        # name then content
        for match in re.finditer(r'<meta[^>]+name=["\']([^"\']+)["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE):
            meta[match.group(1).lower()] = match.group(2)

        # property then content
        for match in re.finditer(r'<meta[^>]+property=["\']([^"\']+)["\'][^>]+content=["\']([^"\']+)["\']', html, re.IGNORECASE):
            meta[match.group(1).lower()] = match.group(2)

        # content then name
        for match in re.finditer(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']([^"\']+)["\']', html, re.IGNORECASE):
            meta[match.group(2).lower()] = match.group(1)

        # content then property
        for match in re.finditer(r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']([^"\']+)["\']', html, re.IGNORECASE):
            meta[match.group(2).lower()] = match.group(1)

        return meta
