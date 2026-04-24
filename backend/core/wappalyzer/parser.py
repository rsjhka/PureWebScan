"""
Wappalyzer Rule Parser.
Parses and compiles Wappalyzer JSON/YAML rules.
"""
import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

_yaml = None


def _load_yaml():
    """Lazy load YAML module."""
    global _yaml
    if _yaml is None:
        import yaml as _yaml_module
        _yaml = _yaml_module
    return _yaml


@dataclass
class TechnologyRule:
    """Parsed technology detection rule."""
    name: str
    slug: str
    description: Optional[str] = None
    website: Optional[str] = None
    categories: List[Dict[str, Any]] = field(default_factory=list)
    icons: Dict[str, Any] = field(default_factory=dict)
    confidence: int = 100

    cookies: Dict = field(default_factory=dict)
    dom: Dict = field(default_factory=dict)
    dns: Dict = field(default_factory=dict)
    headers: Dict = field(default_factory=dict)
    implies: Dict = field(default_factory=dict)
    excludes: Dict = field(default_factory=dict)
    requires: Dict = field(default_factory=dict)
    meta: Dict = field(default_factory=dict)
    probe: Dict = field(default_factory=dict)
    scriptSrc: Dict = field(default_factory=dict)
    scripts: Dict = field(default_factory=dict)
    url: Dict = field(default_factory=dict)
    xhr: Dict = field(default_factory=dict)
    html: Dict = field(default_factory=dict)
    js: Dict = field(default_factory=dict)

    version: Optional[str] = None
    file_path: Optional[str] = None
    raw_rules: Dict = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for python-Wappalyzer compatibility."""
        result = {
            "name": self.name,
            "slug": self.slug,
            "website": self.website,
            "categories": self.categories,
            "icon": list(self.icons.values())[0] if self.icons else "",
            "confidence": self.confidence,
            "version": self.version,
        }

        # Add detection patterns from raw_rules
        if self.raw_rules:
            for key in ["cookies", "dom", "dns", "headers", "excludes", "requires",
                       "meta", "probe", "scriptSrc", "scripts", "url", "xhr", "html", "js"]:
                if key in self.raw_rules:
                    result[key] = self.raw_rules[key]

        if self.implies:
            result["implies"] = self.implies

        return result


class WappalyzerRuleParser:
    """Parser for Wappalyzer technology detection rules."""

    CATEGORIES = {
        "1": {"name": "CMS", "slug": "cms"},
        "2": {"name": "Message Queue", "slug": "message-queue"},
        "3": {"name": "Commerce", "slug": "commerce"},
        "4": {"name": "Database", "slug": "database"},
        "5": {"name": "Documentation Tools", "slug": "documentation-tools"},
        "6": {"name": "Widget", "slug": "widget"},
        "7": {"name": "Finance", "slug": "finance"},
        "8": {"name": "Game Engine", "slug": "game-engine"},
        "9": {"name": "CMS", "slug": "cms"},
        "10": {"name": "Analytics", "slug": "analytics"},
        "11": {"name": "Blogs", "slug": "blogs"},
        "12": {"name": "JavaScript Frameworks", "slug": "javascript-frameworks"},
        "13": {"name": "Tag Managers", "slug": "tag-managers"},
        "14": {"name": "Marketing Automation", "slug": "marketing-automation"},
        "15": {"name": "CDN", "slug": "cdn"},
        "16": {"name": "Live Chat", "slug": "live-chat"},
        "17": {"name": "CRM", "slug": "crm"},
        "18": {"name": "Web Frameworks", "slug": "web-frameworks"},
        "19": {"name": "Font Scripts", "slug": "font-scripts"},
        "20": {"name": "JavaScript Graphics", "slug": "javascript-graphics"},
        "21": {"name": "Media Players", "slug": "media-players"},
        "22": {"name": "Web Servers", "slug": "web-servers"},
        "23": {"name": "Operating Systems", "slug": "operating-systems"},
        "24": {"name": "Programming Languages", "slug": "programming-languages"},
        "25": {"name": "SaaS", "slug": "saas"},
        "26": {"name": "Issue Trackers", "slug": "issue-trackers"},
        "27": {"name": "Build Tools", "slug": "build-tools"},
        "28": {"name": "Rich Text Editors", "slug": "rich-text-editors"},
        "29": {"name": "Web Mail", "slug": "web-mail"},
        "30": {"name": "Queues", "slug": "queues"},
        "31": {"name": "Captcha", "slug": "captcha"},
        "32": {"name": "Comments", "slug": "comments"},
        "33": {"name": "Security", "slug": "security"},
        "34": {"name": "Marketing", "slug": "marketing"},
        "35": {"name": "LMS", "slug": "lms"},
        "36": {"name": "Translation", "slug": "translation"},
        "37": {"name": "SEO", "slug": "seo"},
        "38": {"name": "Video Platforms", "slug": "video-platforms"},
        "39": {"name": "Maps", "slug": "maps"},
        "40": {"name": "Hosting Panels", "slug": "hosting-panels"},
        "41": {"name": "DN", "slug": "dns"},
        "42": {"name": "DevTools", "slug": "devtools"},
        "43": {"name": "Network", "slug": "network"},
        "44": {"name": "Search Engines", "slug": "search-engines"},
        "45": {"name": "Navigation", "slug": "navigation"},
        "46": {"name": "Reviews", "slug": "reviews"},
        "47": {"name": "Performance", "slug": "performance"},
        "48": {"name": "A/B Testing", "slug": "a-b-testing"},
        "49": {"name": "Retargeting", "slug": "retargeting"},
        "50": {"name": "Survey", "slug": "survey"},
        "51": {"name": "Booking", "slug": "booking"},
        "52": {"name": "Cookie Consent", "slug": "cookie-consent"},
        "53": {"name": "Real Estate", "slug": "real-estate"},
        "54": {"name": "Newsletters", "slug": "newsletters"},
        "55": {"name": "Scheduling", "slug": "scheduling"},
        "56": {"name": "Accountants", "slug": "accountants"},
        "57": {"name": "Personnalisation", "slug": "personnalisation"},
        "58": {"name": "Backend", "slug": "backend"},
        "59": {"name": "Payments", "slug": "payments"},
        "60": {"name": "Optimization", "slug": "optimization"},
        "61": {"name": "Location", "slug": "location"},
        "62": {"name": "Cryptominer", "slug": "cryptominer"},
        "63": {"name": "Category", "slug": "category"},
        "64": {"name": "Food", "slug": "food"},
        "65": {"name": "Bandwidth", "slug": "bandwidth"},
        "66": {"name": "Knowledge Bases", "slug": "knowledge-bases"},
        "67": {"name": "HR", "slug": "hr"},
        "68": {"name": "Chat", "slug": "chat"},
        "69": {"name": "Email", "slug": "email"},
        "70": {"name": "Forms", "slug": "forms"},
        "71": {"name": "Announcement", "slug": "announcement"},
        "72": {"name": "Docs", "slug": "docs"},
        "73": {"name": "Ticketing", "slug": "ticketing"},
        "74": {"name": "Surveys", "slug": "surveys"},
        "75": {"name": "API", "slug": "api"},
        "76": {"name": "Bot", "slug": "bot"},
        "77": {"name": "RUM", "slug": "rum"},
        "78": {"name": "UX", "slug": "ux"},
        "79": {"name": "SCRM", "slug": "scrm"},
        "80": {"name": "Accounting", "slug": "accounting"},
        "81": {"name": "Claim", "slug": "claim"},
        "82": {"name": "IT", "slug": "it"},
        "83": {"name": "Cryptocurrencies", "slug": "cryptocurrencies"},
        "84": {"name": "Social", "slug": "social"},
        "85": {"name": "Learning", "slug": "learning"},
        "86": {"name": "Remote", "slug": "remote"},
        "87": {"name": "SEO", "slug": "seo"},
        "88": {"name": "Content", "slug": "content"},
        "89": {"name": "Digital", "slug": "digital"},
        "90": {"name": "Cloud", "slug": "cloud"},
    }

    def __init__(self, rules_dir: Optional[Path] = None):
        """Initialize the rule parser."""
        self.rules_dir = rules_dir
        self.rules: Dict[str, TechnologyRule] = {}
        self.categories = self.CATEGORIES

    def load_all_rules(self) -> int:
        """Load all rule files from the rules directory."""
        if not self.rules_dir or not self.rules_dir.exists():
            logger.warning(f"Rules directory not found: {self.rules_dir}")
            return 0

        loaded_count = 0
        for root, _, files in os.walk(self.rules_dir):
            for filename in files:
                if filename.endswith((".json", ".yml", ".yaml")):
                    filepath = os.path.join(root, filename)
                    try:
                        self.load_rule_file(filepath)
                        loaded_count += 1
                    except Exception as e:
                        logger.error(f"Failed to load rule file {filepath}: {e}")

        logger.info(f"Loaded {len(self.rules)} technology rules from {loaded_count} files")
        return len(self.rules)

    def load_rule_file(self, filepath: str) -> None:
        """Load a single rule file."""
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                if filepath.endswith((".yml", ".yaml")):
                    yaml = _load_yaml()
                    data = yaml.safe_load(f)
                else:
                    data = json.load(f)

            if not data:
                return

            # Handle both old format (with "technologies" key) and new format (direct keys)
            if "technologies" in data:
                # Old format
                categories_data = data.get("categories", {})
                categories = self._parse_categories(categories_data)

                for tech_name, tech_data in data.get("technologies", {}).items():
                    self._parse_technology(tech_name, tech_data, categories, filepath)
            else:
                # New Wappalyzer format - technologies are top-level keys
                categories_data = data.get("categories", {})
                categories = self._parse_categories(categories_data)

                for tech_name, tech_data in data.items():
                    if isinstance(tech_data, dict):
                        self._parse_technology(tech_name, tech_data, categories, filepath)

        except Exception as e:
            logger.error(f"Error loading rule file {filepath}: {e}")
            raise

    def _parse_categories(self, categories_data: Any) -> Dict[str, Any]:
        """Parse categories data."""
        if isinstance(categories_data, dict):
            return {
                str(cat_id): self.categories.get(str(cat_id), {"name": str(cat_id), "slug": str(cat_id)})
                for cat_id in categories_data.keys()
            }
        elif isinstance(categories_data, list):
            return {
                str(cat_id): self.categories.get(str(cat_id), {"name": str(cat_id), "slug": str(cat_id)})
                for cat_id in categories_data
            }
        return {}

    def _parse_technology(
        self,
        name: str,
        data: Dict[str, Any],
        categories: Dict[str, Any],
        filepath: str
    ) -> None:
        """Parse a single technology rule."""
        if name in self.rules:
            return

        slug = name.lower().replace(" ", "-").replace(".", "-").replace("_", "-")

        # Parse categories - can be "cats" (array) or "categories" (dict)
        cat_ids = data.get("cats", [])
        if isinstance(cat_ids, list):
            tech_categories = [
                self.categories.get(str(cat_id), {"name": str(cat_id), "slug": str(cat_id)})
                for cat_id in cat_ids
            ]
        elif isinstance(cat_ids, dict):
            tech_categories = list(cat_ids.values())
        else:
            tech_categories = list(categories.values())

        rule = TechnologyRule(
            name=name,
            slug=slug,
            description=data.get("description"),
            website=data.get("website"),
            categories=tech_categories,
            icons={"icon": data.get("icon", "")},
            confidence=data.get("confidence", 100),
            version=data.get("version"),
            file_path=filepath,
            raw_rules=data
        )

        # Parse implies
        implies_data = data.get("implies")
        if implies_data:
            if isinstance(implies_data, str):
                rule.implies = {implies_data: ""}
            elif isinstance(implies_data, list):
                rule.implies = {item: "" for item in implies_data}
            elif isinstance(implies_data, dict):
                rule.implies = implies_data

        # Parse detection patterns
        for field_name, pattern_data in [
            ("cookies", data.get("cookies")),
            ("dom", data.get("dom")),
            ("dns", data.get("dns")),
            ("headers", data.get("headers")),
            ("excludes", data.get("excludes")),
            ("requires", data.get("requires")),
            ("meta", data.get("meta")),
            ("probe", data.get("probe")),
            ("scriptSrc", data.get("scriptSrc")),
            ("scripts", data.get("scripts")),
            ("url", data.get("url")),
            ("xhr", data.get("xhr")),
            ("html", data.get("html")),
            ("js", data.get("js")),
        ]:
            if pattern_data:
                compiled_patterns = self._compile_patterns(name, field_name, pattern_data)
                if compiled_patterns:
                    setattr(rule, field_name, compiled_patterns)

        self.rules[name] = rule

    def _compile_patterns(
        self,
        tech_name: str,
        field: str,
        patterns: Any
    ) -> Dict:
        """Compile regex patterns for a field.
        
        Wappalyzer format:
        - headers: {"server": "^nginx$"} - key is header name, value is regex
        - scriptSrc: "jquery" or ["jquery", "react"] - patterns as string or list
        - cookies: {"cookie_name": ""} - key is cookie name, value is optional regex
        """
        compiled = {}

        if patterns is None:
            return compiled

        # Handle string pattern
        if isinstance(patterns, str):
            try:
                return {"main": re.compile(patterns, re.IGNORECASE)}
            except re.error as e:
                logger.warning(f"Rule {tech_name}.{field}: Regex compile failed: {e}")
                return {}

        # Handle list of patterns
        if isinstance(patterns, list):
            for i, pattern in enumerate(patterns):
                if isinstance(pattern, str):
                    try:
                        compiled[f"pattern_{i}"] = re.compile(pattern, re.IGNORECASE)
                    except re.error as e:
                        logger.warning(f"Rule {tech_name}.{field}[{i}]: Regex compile failed: {e}")
            return compiled

        # Handle dict patterns
        if isinstance(patterns, dict):
            for key, pattern in patterns.items():
                if isinstance(pattern, str):
                    try:
                        compiled[key] = re.compile(pattern, re.IGNORECASE)
                    except re.error as e:
                        logger.warning(f"Rule {tech_name}.{field}.{key}: Regex compile failed: {e}")

        return compiled

    def get_rule(self, name: str) -> Optional[TechnologyRule]:
        """Get a specific rule by name."""
        return self.rules.get(name)

    def get_rules_by_category(self, category_id: str) -> List[TechnologyRule]:
        """Get all rules in a specific category."""
        return [
            rule for rule in self.rules.values()
            if any(cat.get("slug") == category_id for cat in rule.categories)
        ]

    def get_all_rules(self) -> Dict[str, TechnologyRule]:
        """Get all loaded rules."""
        return self.rules

    def get_category_name(self, category_id: str) -> str:
        """Get category name by ID."""
        return self.categories.get(category_id, {}).get("name", category_id)

    def reload_rules(self) -> int:
        """Reload all rules."""
        self.rules.clear()
        return self.load_all_rules()
