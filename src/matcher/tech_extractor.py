"""Technology stack extractor from job descriptions."""

import re
from typing import List, Set, Dict
from dataclasses import dataclass


@dataclass
class TechCategory:
    """Represents a category of technologies."""
    name: str
    technologies: List[str]


# Comprehensive tech stack database
TECH_DATABASE = {
    "languages": [
        "python", "javascript", "typescript", "java", "c++", "c#", "go", "golang",
        "rust", "ruby", "php", "swift", "kotlin", "scala", "r", "matlab",
        "shell", "bash", "powershell", "sql", "html", "css", "sass", "less"
    ],
    "frontend": [
        "react", "angular", "vue", "vue.js", "svelte", "ember", "backbone",
        "jquery", "bootstrap", "tailwind", "material-ui", "antd", "chakra ui",
        "next.js", "nextjs", "nuxt", "gatsby", "remix", "astro"
    ],
    "backend": [
        "node.js", "nodejs", "express", "django", "flask", "fastapi", "spring",
        "spring boot", "laravel", "rails", "ruby on rails", "asp.net", "gin",
        "fiber", "echo", "actix", "rocket", "nestjs", "nest.js"
    ],
    "databases": [
        "postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch",
        "sqlite", "oracle", "sql server", "mariadb", "cassandra", "dynamodb",
        "firebase", "supabase", "neo4j", "influxdb", "timescaledb"
    ],
    "cloud": [
        "aws", "amazon web services", "azure", "gcp", "google cloud",
        "digitalocean", "heroku", "netlify", "vercel", "cloudflare",
        "linode", "vultr", "oracle cloud", "ibm cloud"
    ],
    "devops": [
        "docker", "kubernetes", "k8s", "jenkins", "gitlab ci", "github actions",
        "circleci", "travis ci", "ansible", "terraform", "puppet", "chef",
        "prometheus", "grafana", "datadog", "new relic", "sentry"
    ],
    "tools": [
        "git", "github", "gitlab", "bitbucket", "jira", "confluence",
        "slack", "notion", "figma", "postman", "insomnia", "wireshark"
    ],
    "testing": [
        "jest", "pytest", "unittest", "mocha", "chai", "cypress", "playwright",
        "selenium", "testcafe", "rspec", "junit", "testng", "karma"
    ],
    "methodologies": [
        "agile", "scrum", "kanban", "tdd", "bdd", "ci/cd", "devops",
        "microservices", "serverless", "event-driven", "rest", "graphql",
        "grpc", "websocket", "mq", "kafka", "rabbitmq"
    ]
}

# Aliases for common technology names
TECH_ALIASES = {
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
    "pg": "postgresql",
    "mongo": "mongodb",
    "k8s": "kubernetes",
    "golang": "go",
    "node": "node.js",
    "reactjs": "react",
    "vuejs": "vue",
    "angularjs": "angular",
}


class TechStackExtractor:
    """Extracts technology stack from job descriptions."""
    
    def __init__(self):
        self.tech_database = TECH_DATABASE
        self.aliases = TECH_ALIASES
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Compile regex patterns for efficient matching."""
        self.patterns = {}
        for category, techs in self.tech_database.items():
            # Create pattern that matches whole words only
            pattern = r'\b(' + '|'.join(re.escape(tech) for tech in techs) + r')\b'
            self.patterns[category] = re.compile(pattern, re.IGNORECASE)
    
    def extract(self, text: str) -> Dict[str, List[str]]:
        """
        Extract technologies from text.
        
        Args:
            text: The job description or any text to analyze
            
        Returns:
            Dictionary mapping categories to lists of found technologies
        """
        if not text:
            return {}
        
        text_lower = text.lower()
        found_techs = {}
        
        for category, pattern in self.patterns.items():
            matches = pattern.findall(text_lower)
            if matches:
                # Normalize and deduplicate
                normalized = set(self._normalize_tech(m) for m in matches)
                found_techs[category] = list(normalized)
        
        return found_techs
    
    def extract_all(self, text: str) -> List[str]:
        """
        Extract all technologies as a flat list.
        
        Args:
            text: The job description or any text to analyze
            
        Returns:
            List of all found technologies
        """
        categorized = self.extract(text)
        all_techs = []
        for techs in categorized.values():
            all_techs.extend(techs)
        return list(set(all_techs))
    
    def _normalize_tech(self, tech: str) -> str:
        """Normalize technology name."""
        tech_lower = tech.lower().strip()
        
        # Check aliases
        if tech_lower in self.aliases:
            return self.aliases[tech_lower]
        
        # Standardize common variations
        normalizations = {
            "node.js": "node.js",
            "nodejs": "node.js",
            "postgresql": "postgresql",
            "postgres": "postgresql",
            "mongodb": "mongodb",
            "mongo": "mongodb",
        }
        
        return normalizations.get(tech_lower, tech_lower)
    
    def get_skill_match_percentage(
        self, 
        job_techs: List[str], 
        user_skills: Set[str]
    ) -> float:
        """
        Calculate match percentage between job requirements and user skills.
        
        Args:
            job_techs: Technologies found in job description
            user_skills: User's skills (lowercase set)
            
        Returns:
            Match percentage (0-100)
        """
        if not job_techs:
            return 0.0
        
        job_techs_lower = set(t.lower() for t in job_techs)
        matched = job_techs_lower.intersection(user_skills)
        
        return (len(matched) / len(job_techs_lower)) * 100
    
    def find_matching_skills(
        self, 
        job_techs: List[str], 
        user_skills: Set[str]
    ) -> tuple:
        """
        Find matching and missing skills.
        
        Args:
            job_techs: Technologies found in job description
            user_skills: User's skills (lowercase set)
            
        Returns:
            Tuple of (matched_skills, missing_skills)
        """
        job_techs_lower = set(t.lower() for t in job_techs)
        matched = job_techs_lower.intersection(user_skills)
        missing = job_techs_lower - user_skills
        
        return list(matched), list(missing)
