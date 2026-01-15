"""PII Stripping utility to sanitize text before sending to AI."""
import re
from typing import Dict, Tuple


class PIIStripper:
    """Strips and restores PII from text for safe AI processing."""
    
    def __init__(self):
        self.mapping: Dict[str, str] = {}
        self.person_counter = 0
    
    def strip(self, text: str) -> Tuple[str, Dict[str, str]]:
        """
        Strip PII from text and return sanitized text + mapping.
        
        Returns:
            Tuple of (sanitized_text, mapping_dict)
        """
        self.mapping = {}
        self.person_counter = 0
        sanitized = text
        
        # Replace emails
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        emails = re.findall(email_pattern, sanitized)
        for i, email in enumerate(emails):
            placeholder = f"[EMAIL_{i+1}]"
            self.mapping[placeholder] = email
            sanitized = sanitized.replace(email, placeholder, 1)
        
        # Replace phone numbers (various formats)
        phone_pattern = r'\b(?:\+?1?[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
        phones = re.findall(phone_pattern, sanitized)
        for i, phone in enumerate(phones):
            placeholder = f"[PHONE_{i+1}]"
            self.mapping[placeholder] = phone
            sanitized = sanitized.replace(phone, placeholder, 1)
        
        # Replace names after keywords (call, email, meet, from, to, with, contact)
        name_keywords = r'\b(call|email|meet|meeting with|from|to|contact|text|message|remind)\s+'
        name_pattern = rf'{name_keywords}([A-Z][a-z]+(?:\s+[A-Z][a-z]+)?)'
        
        def replace_name(match):
            keyword = match.group(1)
            name = match.group(2)
            self.person_counter += 1
            placeholder = f"[PERSON_{self.person_counter}]"
            self.mapping[placeholder] = name
            return f"{keyword} {placeholder}"
        
        sanitized = re.sub(name_pattern, replace_name, sanitized)
        
        return sanitized, self.mapping
    
    def restore(self, text: str, mapping: Dict[str, str]) -> str:
        """
        Restore PII from mapping back into text.
        
        Args:
            text: Sanitized text with placeholders
            mapping: Dictionary mapping placeholders to original values
            
        Returns:
            Text with PII restored
        """
        restored = text
        for placeholder, original in mapping.items():
            restored = restored.replace(placeholder, original)
        return restored


# Singleton instance for easy import
pii_stripper = PIIStripper()


def strip_pii(text: str) -> Tuple[str, Dict[str, str]]:
    """Convenience function to strip PII from text."""
    return pii_stripper.strip(text)


def restore_pii(text: str, mapping: Dict[str, str]) -> str:
    """Convenience function to restore PII to text."""
    return pii_stripper.restore(text, mapping)
