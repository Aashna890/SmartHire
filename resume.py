import re
import PyPDF2
import spacy
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import json
from dataclasses import dataclass, asdict
from pathlib import Path

@dataclass
class ContactInfo:
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    linkedin: Optional[str] = None
    github: Optional[str] = None
    website: Optional[str] = None

@dataclass
class Education:
    degree: Optional[str] = None
    institution: Optional[str] = None
    year: Optional[str] = None
    gpa: Optional[str] = None
    field_of_study: Optional[str] = None

@dataclass
class Experience:
    job_title: Optional[str] = None
    company: Optional[str] = None
    duration: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None
    responsibilities: List[str] = None
    experience_type: Optional[str] = None  # 'work', 'internship', 'freelance', etc.
    location: Optional[str] = None
    is_current: bool = False

@dataclass
class ParsedResume:
    contact_info: ContactInfo
    summary: Optional[str] = None
    skills: List[str] = None
    technical_skills: List[str] = None
    soft_skills: List[str] = None
    work_experience: List[Experience] = None
    internship_experience: List[Experience] = None
    all_experience: List[Experience] = None  # Combined work + internships
    education: List[Education] = None
    certifications: List[str] = None
    projects: List[str] = None
    languages: List[str] = None
    years_of_experience: Optional[int] = None
    total_internship_months: Optional[int] = None

class ResumeParser:
    def __init__(self):
        """Initialize the resume parser with NLP model and skill databases."""
        # Load spaCy model (install with: python -m spacy download en_core_web_sm)
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Warning: spaCy model not found. Install with: python -m spacy download en_core_web_sm")
            self.nlp = None
        
        # Common technical skills database
        self.technical_skills = {
            'programming_languages': [
                'python', 'java', 'javascript', 'typescript', 'c++', 'c#', 'c', 'go', 'rust', 'php',
                'ruby', 'swift', 'kotlin', 'scala', 'r', 'matlab', 'perl', 'shell', 'bash', 'powershell'
            ],
            'web_technologies': [
                'html', 'css', 'react', 'angular', 'vue', 'node.js', 'express', 'django', 'flask',
                'spring', 'laravel', 'bootstrap', 'jquery', 'sass', 'less', 'webpack', 'vite'
            ],
            'databases': [
                'mysql', 'postgresql', 'mongodb', 'redis', 'sqlite', 'oracle', 'sql server',
                'cassandra', 'dynamodb', 'elasticsearch', 'neo4j'
            ],
            'cloud_platforms': [
                'aws', 'azure', 'gcp', 'google cloud', 'heroku', 'digitalocean', 'linode',
                'cloudflare', 'vercel', 'netlify'
            ],
            'tools_frameworks': [
                'docker', 'kubernetes', 'jenkins', 'git', 'github', 'gitlab', 'bitbucket',
                'jira', 'confluence', 'slack', 'trello', 'asana', 'terraform', 'ansible'
            ],
            'data_science': [
                'pandas', 'numpy', 'scikit-learn', 'tensorflow', 'pytorch', 'keras',
                'matplotlib', 'seaborn', 'plotly', 'jupyter', 'tableau', 'power bi'
            ]
        }
        
        # Soft skills database
        self.soft_skills = [
            'leadership', 'communication', 'teamwork', 'problem solving', 'critical thinking',
            'time management', 'project management', 'adaptability', 'creativity', 'collaboration',
            'analytical thinking', 'attention to detail', 'multitasking', 'decision making',
            'conflict resolution', 'negotiation', 'presentation skills', 'customer service'
        ]
        
        # Common degree patterns
        self.degree_patterns = [
            r'bachelor.*?(?:computer science|engineering|mathematics|physics|chemistry)',
            r'master.*?(?:computer science|engineering|business|mba)',
            r'phd.*?(?:computer science|engineering|mathematics|physics)',
            r'b\.?(?:sc|tech|eng|com|a)',
            r'm\.?(?:sc|tech|eng|com|ba|s)',
            r'(?:bachelor|master|phd|doctorate)',
        ]

    def extract_text_from_pdf(self, pdf_path: str) -> str:
        """Extract text from PDF file."""
        try:
            text = ""
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"Error extracting text from PDF: {e}")
            return ""

    def extract_contact_info(self, text: str) -> ContactInfo:
        """Extract contact information from resume text."""
        contact = ContactInfo()
        
        # Extract email
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, text)
        contact.email = emails[0] if emails else None
        
        # Extract phone number
        phone_patterns = [
            r'[\+]?[\d\s\-\(\)]{10,}',
            r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+\d{1,3}[-.\s]?\d{3,}[-.\s]?\d{3,}[-.\s]?\d{4}'
        ]
        for pattern in phone_patterns:
            phones = re.findall(pattern, text)
            if phones:
                contact.phone = phones[0].strip()
                break
        
        # Extract LinkedIn
        linkedin_pattern = r'(?:linkedin\.com/in/|linkedin\.com/profile/view\?id=)([A-Za-z0-9\-]+)'
        linkedin_matches = re.findall(linkedin_pattern, text.lower())
        if linkedin_matches:
            contact.linkedin = f"linkedin.com/in/{linkedin_matches[0]}"
        
        # Extract GitHub
        github_pattern = r'(?:github\.com/)([A-Za-z0-9\-]+)'
        github_matches = re.findall(github_pattern, text.lower())
        if github_matches:
            contact.github = f"github.com/{github_matches[0]}"
        
        # Extract name (assume first line or first proper noun)
        if self.nlp:
            doc = self.nlp(text[:500])  # First 500 chars
            for ent in doc.ents:
                if ent.label_ == "PERSON":
                    contact.name = ent.text
                    break
        
        if not contact.name:
            # Fallback: extract from first line
            lines = text.split('\n')
            for line in lines[:5]:
                line = line.strip()
                if line and not any(char.isdigit() or '@' in line for char in line):
                    if len(line.split()) >= 2:
                        contact.name = line
                        break
        
        return contact

    def extract_skills(self, text: str) -> Tuple[List[str], List[str], List[str]]:
        """Extract technical skills, soft skills, and all skills from resume."""
        text_lower = text.lower()
        
        # Extract technical skills with context-aware matching
        found_technical_skills = []
        for category, skills in self.technical_skills.items():
            for skill in skills:
                if self._is_skill_present(skill, text_lower):
                    found_technical_skills.append(skill)
        
        # Extract soft skills
        found_soft_skills = []
        for skill in self.soft_skills:
            if self._is_skill_present(skill, text_lower):
                found_soft_skills.append(skill)
        
        # Combine all skills
        all_skills = found_technical_skills + found_soft_skills
        
        # Remove duplicates while preserving order
        all_skills = list(dict.fromkeys(all_skills))
        found_technical_skills = list(dict.fromkeys(found_technical_skills))
        found_soft_skills = list(dict.fromkeys(found_soft_skills))
        
        return all_skills, found_technical_skills, found_soft_skills

    def _is_skill_present(self, skill: str, text_lower: str) -> bool:
        """Check if a skill is present in text with context-aware matching."""
        skill_lower = skill.lower()
        
        # Special handling for problematic short skills
        problematic_skills = {
            'go': ['golang', 'go programming', 'go language', 'go dev'],
            'r': ['r programming', 'r language', 'r statistical', 'r studio', 'rstudio'],
            'c': ['c programming', 'c language', 'c/c++', 'c++'],
        }
        
        # For problematic skills, require more specific context
        if skill_lower in problematic_skills:
            context_patterns = problematic_skills[skill_lower]
            return any(pattern in text_lower for pattern in context_patterns)
        
        # For short skills (1-2 characters), require word boundaries
        if len(skill_lower) <= 2:
            pattern = r'\b' + re.escape(skill_lower) + r'\b'
            matches = re.findall(pattern, text_lower)
            
            # Additional context check for single letters
            if len(skill_lower) == 1:
                # Look for programming context around the match
                programming_context = ['programming', 'language', 'coding', 'development', 'script']
                for match in re.finditer(pattern, text_lower):
                    start, end = match.span()
                    # Check 50 characters before and after the match
                    context = text_lower[max(0, start-50):min(len(text_lower), end+50)]
                    if any(ctx in context for ctx in programming_context):
                        return True
                return False
            
            return len(matches) > 0
        
        # For longer skills, use simple substring matching
        if len(skill_lower) >= 3:
            return skill_lower in text_lower
        
        return False

    def extract_experience(self, text: str) -> Tuple[List[Experience], List[Experience], List[Experience]]:
        """Extract work experience and internships from resume."""
        all_experiences = []
        work_experiences = []
        internship_experiences = []
        
        # Common experience section headers
        experience_patterns = [
            r'(?:work\s+)?experience',
            r'employment\s+history',
            r'professional\s+experience',
            r'career\s+history',
            r'work\s+history'
        ]
        
        # Internship section headers
        internship_patterns = [
            r'internships?',
            r'intern\s+experience',
            r'summer\s+internships?',
            r'industrial\s+training',
            r'co-op\s+experience'
        ]
        
        # Keywords that indicate internship vs work
        internship_keywords = [
            'intern', 'internship', 'trainee', 'co-op', 'summer intern',
            'graduate trainee', 'industrial training', 'apprentice'
        ]
        
        work_keywords = [
            'employee', 'developer', 'engineer', 'manager', 'analyst',
            'specialist', 'consultant', 'lead', 'senior', 'junior',
            'associate', 'executive', 'director', 'coordinator'
        ]
        
        # Find all experience sections
        sections_found = []
        
        # Look for work experience sections
        for pattern in experience_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sections_found.append(('work', match.start(), match.end()))
        
        # Look for internship sections
        for pattern in internship_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                sections_found.append(('internship', match.start(), match.end()))
        
        # If no specific sections found, look for general experience
        if not sections_found:
            general_pattern = r'experience|employment'
            match = re.search(general_pattern, text, re.IGNORECASE)
            if match:
                sections_found.append(('general', match.start(), match.end()))
        
        for section_type, start_pos, end_pos in sections_found:
            # Find the end of this section
            next_sections = [
                'education', 'skills', 'projects', 'certifications', 
                'awards', 'publications', 'references', 'interests'
            ]
            section_end = len(text)
            section_start = end_pos
            
            for next_section in next_sections:
                next_match = re.search(next_section, text[section_start:], re.IGNORECASE)
                if next_match:
                    section_end = section_start + next_match.start()
                    break
            
            section_text = text[section_start:section_end]
            section_experiences = self._parse_experience_section(section_text, section_type)
            
            for exp in section_experiences:
                all_experiences.append(exp)
                if exp.experience_type == 'internship':
                    internship_experiences.append(exp)
                else:
                    work_experiences.append(exp)
        
        # If no structured sections, try to parse the entire text for experience patterns
        if not all_experiences:
            all_experiences = self._extract_experience_from_full_text(text)
            
            # Classify experiences
            for exp in all_experiences:
                if any(keyword in exp.job_title.lower() for keyword in internship_keywords if exp.job_title):
                    exp.experience_type = 'internship'
                    internship_experiences.append(exp)
                else:
                    exp.experience_type = 'work'
                    work_experiences.append(exp)
        
        return all_experiences, work_experiences, internship_experiences

    def _parse_experience_section(self, section_text: str, section_type: str) -> List[Experience]:
        """Parse individual experience section and extract job entries."""
        experiences = []
        lines = [line.strip() for line in section_text.split('\n') if line.strip()]
        
        current_exp = None
        i = 0
        
        while i < len(lines):
            line = lines[i]
            
            # Skip empty lines and common headers
            if not line or line.lower() in ['experience', 'work experience', 'internships', 'employment history']:
                i += 1
                continue
            
            # Check if this line looks like a job title
            if self._is_job_title_line(line):
                # Save previous experience
                if current_exp and current_exp.job_title:
                    experiences.append(current_exp)
                
                # Start new experience
                current_exp = Experience()
                current_exp.job_title = line.strip()
                current_exp.experience_type = 'internship' if section_type == 'internship' else 'work'
                
                # Look ahead for company name (usually next line)
                if i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if self._looks_like_company(next_line) and not self._contains_date(next_line):
                        current_exp.company = next_line
                        i += 1
                
                # Look for duration/dates in next few lines
                for j in range(i + 1, min(i + 4, len(lines))):
                    if self._contains_date(lines[j]):
                        current_exp.duration = lines[j].strip()
                        dates = self._extract_dates(lines[j])
                        if dates:
                            current_exp.start_date = dates[0]
                            current_exp.end_date = dates[1] if len(dates) > 1 else None
                            current_exp.is_current = 'present' in lines[j].lower() or 'current' in lines[j].lower()
                        break
            
            # Check if line contains dates (might be duration line)
            elif current_exp and self._contains_date(line):
                if not current_exp.duration:
                    current_exp.duration = line
                    dates = self._extract_dates(line)
                    if dates:
                        current_exp.start_date = dates[0]
                        current_exp.end_date = dates[1] if len(dates) > 1 else None
                        current_exp.is_current = 'present' in line.lower() or 'current' in line.lower()
            
            # Check if line looks like a company name
            elif current_exp and not current_exp.company and self._looks_like_company(line):
                current_exp.company = line
            
            # Otherwise, treat as description/responsibility
            elif current_exp:
                if not current_exp.description:
                    current_exp.description = line
                else:
                    current_exp.description += " " + line
                
                # Add to responsibilities if it starts with bullet point or action verb
                if line.startswith(('•', '-', '*')) or self._starts_with_action_verb(line):
                    if not current_exp.responsibilities:
                        current_exp.responsibilities = []
                    current_exp.responsibilities.append(line.lstrip('•-* '))
            
            i += 1
        
        # Add the last experience
        if current_exp and current_exp.job_title:
            experiences.append(current_exp)
        
        return experiences

    def _extract_experience_from_full_text(self, text: str) -> List[Experience]:
        """Fallback method to extract experience from full text when no clear sections exist."""
        experiences = []
        
        # Look for common job title patterns
        job_patterns = [
            r'(?:^|\n)\s*([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Manager|Analyst|Specialist|Intern|Consultant|Director|Coordinator|Lead|Senior|Junior|Associate))\s*\n',
            r'(?:^|\n)\s*([A-Z][a-zA-Z\s]+)\s*(?:-|at|@)\s*([A-Z][a-zA-Z\s&.,]+)\s*\n',
        ]
        
        for pattern in job_patterns:
            matches = re.finditer(pattern, text, re.MULTILINE)
            for match in matches:
                exp = Experience()
                exp.job_title = match.group(1).strip()
                if match.lastindex > 1:
                    exp.company = match.group(2).strip()
                experiences.append(exp)
        
        return experiences

    def _is_job_title_line(self, line: str) -> bool:
        """Check if a line looks like a job title."""
        line_lower = line.lower().strip()
        
        # Common job title indicators
        job_indicators = [
            'engineer', 'developer', 'manager', 'analyst', 'specialist',
            'intern', 'consultant', 'director', 'coordinator', 'lead',
            'senior', 'junior', 'associate', 'executive', 'designer',
            'architect', 'scientist', 'researcher', 'administrator',
            'supervisor', 'assistant', 'officer', 'representative'
        ]
        
        # Check if line contains job indicators
        if any(indicator in line_lower for indicator in job_indicators):
            return True
        
        # Check if line is title case and reasonable length
        if line.istitle() and 2 <= len(line.split()) <= 6:
            return True
        
        return False

    def _looks_like_company(self, line: str) -> bool:
        """Check if a line looks like a company name."""
        # Skip if it looks like a date or description
        if self._contains_date(line) or len(line.split()) > 8:
            return False
        
        # Company indicators
        company_suffixes = ['inc', 'corp', 'llc', 'ltd', 'pvt', 'technologies', 'systems', 'solutions']
        if any(suffix in line.lower() for suffix in company_suffixes):
            return True
        
        # Check if it's a proper noun format
        if line.replace(' ', '').replace('.', '').replace(',', '').replace('&', '').isalpha():
            words = line.split()
            if 1 <= len(words) <= 5 and all(word[0].isupper() for word in words if word):
                return True
        
        return False

    def _contains_date(self, line: str) -> bool:
        """Check if line contains date information."""
        date_patterns = [
            r'\d{4}',  # Year
            r'\d{1,2}/\d{4}',  # MM/YYYY
            r'\d{1,2}-\d{4}',  # MM-YYYY
            r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)',  # Month names
            r'present|current|ongoing',  # Present indicators
        ]
        
        return any(re.search(pattern, line.lower()) for pattern in date_patterns)

    def _extract_dates(self, text: str) -> List[str]:
        """Extract start and end dates from text."""
        dates = []
        
        # Find years
        years = re.findall(r'\d{4}', text)
        dates.extend(years)
        
        # Find month-year patterns
        month_year = re.findall(r'(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{4}', text.lower())
        dates.extend(month_year)
        
        # Check for present
        if re.search(r'present|current|ongoing', text.lower()):
            dates.append('present')
        
        return dates[:2]  # Return max 2 dates (start, end)

    def _starts_with_action_verb(self, line: str) -> bool:
        """Check if line starts with an action verb (common in job descriptions)."""
        action_verbs = [
            'managed', 'developed', 'created', 'implemented', 'designed', 'built',
            'led', 'coordinated', 'analyzed', 'maintained', 'improved', 'optimized',
            'collaborated', 'worked', 'assisted', 'supported', 'delivered', 'executed',
            'established', 'streamlined', 'enhanced', 'resolved', 'troubleshot'
        ]
        
        first_word = line.split()[0].lower().rstrip('.,!?;:') if line.split() else ''
        return first_word in action_verbs

    def extract_education(self, text: str) -> List[Education]:
        """Extract education information from resume."""
        education_list = []
        
        # Find education section
        education_pattern = r'education'
        match = re.search(education_pattern, text, re.IGNORECASE)
        
        if match:
            start_pos = match.start()
            # Find next major section
            next_sections = ['experience', 'skills', 'projects', 'certifications']
            end_pos = len(text)
            for section in next_sections:
                section_match = re.search(section, text[start_pos:], re.IGNORECASE)
                if section_match:
                    end_pos = start_pos + section_match.start()
                    break
            
            education_section = text[start_pos:end_pos]
            
            # Extract degree information
            for pattern in self.degree_patterns:
                matches = re.findall(pattern, education_section, re.IGNORECASE)
                for match in matches:
                    edu = Education()
                    edu.degree = match
                    education_list.append(edu)
        
        return education_list

    def calculate_experience_metrics(self, work_experiences: List[Experience], internship_experiences: List[Experience]) -> Tuple[int, int]:
        """Calculate total years of work experience and total months of internships."""
        total_work_years = 0
        total_internship_months = 0
        current_year = datetime.now().year
        current_month = datetime.now().month
        
        # Calculate work experience
        for exp in work_experiences:
            if exp.duration:
                years = self._calculate_duration_years(exp.duration, current_year)
                total_work_years += years
        
        # Calculate internship experience (in months)
        for exp in internship_experiences:
            if exp.duration:
                months = self._calculate_duration_months(exp.duration, current_year, current_month)
                total_internship_months += months
        
        return total_work_years, total_internship_months

    def _calculate_duration_years(self, duration_str: str, current_year: int) -> int:
        """Calculate years from duration string."""
        # Extract years from duration string
        years = re.findall(r'\d{4}', duration_str)
        if len(years) >= 2:
            start_year = int(years[0])
            end_year = int(years[1])
            return max(0, end_year - start_year)
        elif len(years) == 1:
            if 'present' in duration_str.lower() or 'current' in duration_str.lower():
                return max(0, current_year - int(years[0]))
            else:
                return 1  # Assume 1 year if only one year mentioned
        
        return 0

    def _calculate_duration_months(self, duration_str: str, current_year: int, current_month: int) -> int:
        """Calculate months from duration string."""
        duration_lower = duration_str.lower()
        
        # Look for explicit month mentions
        month_patterns = [
            (r'(\d+)\s*months?', 1),
            (r'(\d+)\s*weeks?', 0.23),  # ~1/4 month per week
            (r'summer', 3),  # Summer internships are typically 3 months
            (r'winter', 2),  # Winter internships are typically 2 months
        ]
        
        for pattern, multiplier in month_patterns:
            match = re.search(pattern, duration_lower)
            if match:
                return int(float(match.group(1)) * multiplier)
        
        # If no explicit months, calculate from years
        years = self._calculate_duration_years(duration_str, current_year)
        if years > 0:
            return years * 12
        
        # Default assumption for internships without clear duration
        if any(keyword in duration_lower for keyword in ['intern', 'summer', 'training']):
            return 3  # Default 3 months for internships
        
        return 6  # Default 6 months for other positions

    def extract_summary(self, text: str) -> Optional[str]:
        """Extract professional summary or objective."""
        summary_patterns = [
            r'(?:professional\s+)?summary',
            r'objective',
            r'profile',
            r'about\s+me'
        ]
        
        for pattern in summary_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                start_pos = match.end()
                # Get next few sentences
                summary_section = text[start_pos:start_pos+500]
                lines = summary_section.split('\n')
                summary_lines = []
                for line in lines[:5]:  # Get first 5 lines
                    line = line.strip()
                    if line and not re.match(r'^[A-Z\s]+$', line):  # Skip headers
                        summary_lines.append(line)
                return ' '.join(summary_lines)
        
        return None

    def parse_resume(self, pdf_path: str) -> ParsedResume:
        """Main method to parse resume and extract all information."""
        # Extract text from PDF
        text = self.extract_text_from_pdf(pdf_path)
        
        if not text:
            return ParsedResume(contact_info=ContactInfo())
        
        # Extract all information
        contact_info = self.extract_contact_info(text)
        skills, technical_skills, soft_skills = self.extract_skills(text)
        all_experience, work_experience, internship_experience = self.extract_experience(text)
        education = self.extract_education(text)
        summary = self.extract_summary(text)
        
        # Calculate experience metrics
        years_exp, internship_months = self.calculate_experience_metrics(work_experience, internship_experience)
        
        # Create parsed resume object
        parsed_resume = ParsedResume(
            contact_info=contact_info,
            summary=summary,
            skills=skills,
            technical_skills=technical_skills,
            soft_skills=soft_skills,
            all_experience=all_experience,
            work_experience=work_experience,
            internship_experience=internship_experience,
            education=education,
            years_of_experience=years_exp,
            total_internship_months=internship_months
        )
        
        return parsed_resume

    def save_parsed_resume(self, parsed_resume: ParsedResume, output_path: str):
        """Save parsed resume data to JSON file."""
        with open(output_path, 'w') as f:
            json.dump(asdict(parsed_resume), f, indent=2, default=str)

def main():
    """Example usage of the resume parser."""
    parser = ResumeParser()
    
    # Example usage
    pdf_path = "tmp/Resume.pdf"  # Replace with actual PDF path
    
    try:
        # Parse the resume
        parsed_resume = parser.parse_resume(pdf_path)
        
        # Display results
        print("=== PARSED RESUME ===")
        print(f"Name: {parsed_resume.contact_info.name}")
        print(f"Email: {parsed_resume.contact_info.email}")
        print(f"Phone: {parsed_resume.contact_info.phone}")
        print(f"LinkedIn: {parsed_resume.contact_info.linkedin}")
        print(f"GitHub: {parsed_resume.contact_info.github}")
        
        print(f"\n=== EXPERIENCE SUMMARY ===")
        print(f"Total Work Experience: {parsed_resume.years_of_experience} years")
        print(f"Total Internship Experience: {parsed_resume.total_internship_months} months")
        
        print(f"\n=== WORK EXPERIENCE ({len(parsed_resume.work_experience or [])} positions) ===")
        for exp in (parsed_resume.work_experience or []):
            print(f"• {exp.job_title} at {exp.company}")
            print(f"  Duration: {exp.duration}")
            if exp.responsibilities:
                print(f"  Key Responsibilities: {len(exp.responsibilities)} listed")
        
        print(f"\n=== INTERNSHIP EXPERIENCE ({len(parsed_resume.internship_experience or [])} positions) ===")
        for exp in (parsed_resume.internship_experience or []):
            print(f"• {exp.job_title} at {exp.company}")
            print(f"  Duration: {exp.duration}")
            print(f"  Type: {exp.experience_type}")
        
        print(f"\n=== SKILLS ===")
        print(f"Technical Skills ({len(parsed_resume.technical_skills)}): {', '.join(parsed_resume.technical_skills[:10])}")
        if len(parsed_resume.technical_skills) > 10:
            print(f"  ... and {len(parsed_resume.technical_skills) - 10} more")
        
        print(f"Soft Skills ({len(parsed_resume.soft_skills)}): {', '.join(parsed_resume.soft_skills[:5])}")
        if len(parsed_resume.soft_skills) > 5:
            print(f"  ... and {len(parsed_resume.soft_skills) - 5} more")
        
        print(f"\n=== EDUCATION ({len(parsed_resume.education or [])} entries) ===")
        for edu in (parsed_resume.education or []):
            print(f"• {edu.degree} from {edu.institution}")
        
        # Save to JSON
        output_path = "parsed_resume.json"
        parser.save_parsed_resume(parsed_resume, output_path)
        print(f"\n✅ Parsed resume saved to: {output_path}")
        
        # Additional statistics
        print(f"\n=== PARSING STATISTICS ===")
        print(f"Total experience entries: {len(parsed_resume.all_experience or [])}")
        print(f"Total skills found: {len(parsed_resume.skills or [])}")
        print(f"Summary extracted: {'Yes' if parsed_resume.summary else 'No'}")
        
    except FileNotFoundError:
        print(f"❌ Error: PDF file '{pdf_path}' not found.")
        print("Please provide a valid PDF file path.")
    except Exception as e:
        print(f"❌ Error parsing resume: {e}")

if __name__ == "__main__":
    main()