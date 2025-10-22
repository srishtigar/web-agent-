"""
domain_helper.py
LLM-Based Domain Detection and Specialized Extraction Strategy
Automatically adapts to any website type without manual pattern updates
"""

import logging
from typing import Dict, Any, List, Tuple
from bs4 import BeautifulSoup
import re

logger = logging.getLogger(__name__)


class DomainDetector:
    """
    LLM-powered domain detection system
    Intelligently classifies websites and suggests extraction strategies
    """
    
    def __init__(self, llm):
        self.llm = llm
        self.detection_cache = {}
    
    def detect_domain(self, url: str, html_content: str) -> Dict[str, Any]:
        """
        Detect website domain type using LLM analysis
        
        Args:
            url: Website URL
            html_content: Raw HTML content
            
        Returns:
            Dictionary with domain info, confidence, and extraction strategy
        """
        # Check cache
        if url in self.detection_cache:
            logger.info("Using cached domain detection for {}".format(url))
            return self.detection_cache[url]
        
        try:
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # Remove unwanted elements
            for tag in soup(['script', 'style', 'nav', 'footer', 'aside']):
                tag.extract()
            
            # Get sample content (first 3000 chars)
            sample_text = soup.get_text()[:3000]
            
            # Extract meta information
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            meta_description = meta_desc.get('content', '') if meta_desc else ''
            
            # Get page title
            title = soup.find('title')
            page_title = title.get_text(strip=True) if title else ''
            
            detection_prompt = """Analyze this webpage and classify its domain type.

URL: {}
TITLE: {}
META DESCRIPTION: {}

CONTENT SAMPLE:
{}

Classify as ONE of these domains:
1. STOCK/FINANCIAL - Stock prices, market data, financial information, trading
2. ECOMMERCE - Products for sale, shopping, online store
3. NEWS - News articles, journalism, current events
4. CORPORATE - Company website, about us, business services
5. BLOG - Personal/professional blog, articles, opinion pieces
6. DOCUMENTATION - Technical docs, API reference, developer guides
7. SOCIAL_MEDIA - Social network, user profiles, community
8. GENERAL - Other types of websites

Respond in this EXACT format (one per line):
DOMAIN: [domain name from list above]
CONFIDENCE: [0-100]
KEY_DATA: [comma-separated list of what specific data to extract]
STRATEGY: [one-line extraction strategy]

Example:
DOMAIN: STOCK/FINANCIAL
CONFIDENCE: 95
KEY_DATA: stock_price, market_cap, pe_ratio, volume, day_high, day_low
STRATEGY: Prioritize tables and numerical data, extract exact prices with decimals

Your response:""".format(url, page_title, meta_description, sample_text)
            
            response = self.llm.invoke(detection_prompt).content
            
            # Parse LLM response
            result = self._parse_detection_response(response)
            result['url'] = url
            
            # Cache result
            self.detection_cache[url] = result
            
            logger.info("Domain detected: {} (confidence: {}%)".format(
                result['domain'], result['confidence']
            ))
            
            return result
            
        except Exception as e:
            logger.error("Domain detection error: {}".format(str(e)))
            return self._get_fallback_result(url)
    
    def _parse_detection_response(self, response: str) -> Dict[str, Any]:
        """Parse LLM detection response"""
        domain = "GENERAL"
        confidence = 50
        key_data = []
        strategy = "Extract main content and key information"
        
        try:
            for line in response.split('\n'):
                line = line.strip()
                
                if line.startswith('DOMAIN:'):
                    domain = line.replace('DOMAIN:', '').strip().upper()
                elif line.startswith('CONFIDENCE:'):
                    try:
                        conf_str = line.replace('CONFIDENCE:', '').strip()
                        confidence = int(re.search(r'\d+', conf_str).group())
                    except:
                        confidence = 50
                elif line.startswith('KEY_DATA:'):
                    data_str = line.replace('KEY_DATA:', '').strip()
                    key_data = [x.strip() for x in data_str.split(',') if x.strip()]
                elif line.startswith('STRATEGY:'):
                    strategy = line.replace('STRATEGY:', '').strip()
        except Exception as e:
            logger.warning("Error parsing detection response: {}".format(str(e)))
        
        return {
            'domain': domain,
            'confidence': confidence,
            'key_data_types': key_data,
            'strategy': strategy
        }
    
    def _get_fallback_result(self, url: str) -> Dict[str, Any]:
        """Fallback result if detection fails"""
        return {
            'url': url,
            'domain': 'GENERAL',
            'confidence': 0,
            'key_data_types': [],
            'strategy': 'Extract all available content'
        }


class ExtractionStrategyGenerator:
    """
    Generates domain-specific extraction instructions for the LLM
    """
    
    # Domain-specific instruction templates
    INSTRUCTIONS = {
        'STOCK/FINANCIAL': """
🏦 FINANCIAL DATA EXTRACTION MODE ACTIVATED

This is a STOCK/FINANCIAL website. Follow these CRITICAL rules:

1. EXACT NUMBERS REQUIRED:
   - Extract stock prices with EXACT decimals (e.g., ₹1,234.56 NOT "around 1200")
   - Include currency symbols (₹, $, etc.)
   - Preserve all decimal places

2. KEY METRICS TO FIND:
   - Current Stock Price (NSE/BSE)
   - Market Capitalization
   - P/E Ratio
   - Volume
   - Day High/Low
   - 52-Week High/Low
   - EPS (Earnings Per Share)
   - Dividend Yield

3. DATA SOURCES (in priority order):
   - Tables (most accurate)
   - Structured data sections
   - Bold/highlighted numbers
   - Price indicators

4. FORMAT YOUR RESPONSE:
   - Label each metric clearly
   - Report "Data not available" if metric not found
   - Always include units (Cr, %, etc.)

Example Output:
• Current Price: ₹1,234.56
• Market Cap: ₹50,000 Cr
• P/E Ratio: 23.45
• Volume: 1,234,567
• Day High: ₹1,250.00
• Day Low: ₹1,220.00
""",
        
        'ECOMMERCE': """
🛒 E-COMMERCE EXTRACTION MODE ACTIVATED

This is an E-COMMERCE/SHOPPING website. Follow these rules:

1. PRODUCT INFORMATION:
   - Extract exact product name/title
   - Extract complete product description
   - Note color, size, variant options

2. PRICING (CRITICAL):
   - MRP (Maximum Retail Price)
   - Selling Price/Offer Price
   - Discount percentage
   - Savings amount

3. RATINGS & REVIEWS:
   - Star rating (e.g., 4.5/5)
   - Number of reviews
   - Number of ratings

4. AVAILABILITY:
   - In Stock / Out of Stock
   - Delivery information
   - Estimated delivery date

5. SPECIFICATIONS:
   - Key product features
   - Technical specifications
   - Dimensions/weight if relevant

DO NOT INCLUDE:
   - Recommended products
   - Advertisements
   - Similar product suggestions

Example Output:
• Product: Samsung Galaxy S24 Ultra (256GB, Titanium Black)
• MRP: ₹1,29,999
• Selling Price: ₹1,09,999
• Discount: 15% off (Save ₹20,000)
• Rating: 4.6/5 (2,345 ratings)
• Availability: In Stock
• Key Features: [list main features]
""",
        
        'NEWS': """
📰 NEWS ARTICLE EXTRACTION MODE ACTIVATED

This is a NEWS website. Follow these rules:

1. ARTICLE METADATA:
   - Headline/Title (exact text)
   - Publication date
   - Author name
   - News agency/source

2. CONTENT SUMMARY:
   - Lead paragraph (first 2-3 paragraphs)
   - Key facts in bullet points
   - Important statistics/numbers mentioned
   - Direct quotes from sources

3. CONTEXT:
   - Who, What, When, Where, Why
   - Background information
   - Impact/significance

DO NOT INCLUDE:
   - Advertisements
   - Recommended articles
   - Comments section
   - Social sharing buttons

Example Output:
• Headline: [exact headline]
• Published: [date]
• Author: [name]
• Summary:
  - [Key point 1]
  - [Key point 2]
  - [Key point 3]
• Key Quote: "[direct quote]"
• Impact: [significance]
""",
        
        'CORPORATE': """
🏢 CORPORATE WEBSITE EXTRACTION MODE ACTIVATED

This is a CORPORATE/BUSINESS website. Extract:

1. COMPANY OVERVIEW:
   - Company name and tagline
   - Industry/sector
   - Founded year
   - Company size (employees/locations)

2. PRODUCTS & SERVICES:
   - Main products/services offered
   - Key features/benefits
   - Target market

3. COMPANY INFORMATION:
   - Mission statement
   - Vision statement
   - Core values
   - Leadership team

4. CONTACT & LOCATION:
   - Headquarters location
   - Contact information
   - Office addresses

5. ACHIEVEMENTS:
   - Awards/recognition
   - Milestones
   - Client testimonials

Example Output:
• Company: [Name]
• Industry: [Sector]
• Founded: [Year]
• Overview: [Brief description]
• Products/Services: [List]
• Leadership: [Key executives]
• Contact: [Details]
""",
        
        'BLOG': """
✍️ BLOG/ARTICLE EXTRACTION MODE ACTIVATED

This is a BLOG or ARTICLE website. Extract:

1. ARTICLE DETAILS:
   - Title (exact text)
   - Author name
   - Publication date
   - Reading time (if available)
   - Categories/tags

2. CONTENT STRUCTURE:
   - Introduction/hook
   - Main points (3-5 bullets)
   - Key takeaways
   - Conclusion

3. SUPPORTING ELEMENTS:
   - Important quotes
   - Statistics mentioned
   - Examples given
   - Actionable advice

DO NOT INCLUDE:
   - Author bio section
   - Comments
   - Related posts
   - Newsletter signups

Example Output:
• Title: [exact title]
• Author: [name]
• Published: [date]
• Topic: [main subject]
• Main Points:
  1. [Point 1]
  2. [Point 2]
  3. [Point 3]
• Key Takeaway: [summary]
• Action Items: [if applicable]
""",
        
        'DOCUMENTATION': """
📚 DOCUMENTATION EXTRACTION MODE ACTIVATED

This is a DOCUMENTATION/TECHNICAL website. Extract:

1. TOPIC/SUBJECT:
   - Main topic being documented
   - Version/release information
   - Last updated date

2. GETTING STARTED:
   - Installation instructions
   - Prerequisites
   - Quick start guide

3. TECHNICAL DETAILS:
   - API endpoints (if applicable)
   - Parameters and their types
   - Return values
   - Error codes

4. EXAMPLES:
   - Code examples (preserve formatting)
   - Usage examples
   - Best practices

5. REFERENCE:
   - Function/method signatures
   - Configuration options
   - Available commands

Example Output:
• Topic: [main subject]
• Purpose: [what it does]
• Installation: [steps]
• Usage: [how to use]
• Example: [code sample]
• Parameters: [list with types]
""",
        
        'SOCIAL_MEDIA': """
👥 SOCIAL MEDIA EXTRACTION MODE ACTIVATED

This is a SOCIAL MEDIA website. Extract:

1. PROFILE INFORMATION:
   - Username/handle
   - Display name
   - Bio/description
   - Follower count
   - Following count

2. CONTENT:
   - Recent posts (top 3-5)
   - Post engagement (likes, shares, comments)
   - Hashtags used

3. ACCOUNT DETAILS:
   - Account type (personal/business/verified)
   - Location
   - Website links
   - Join date

Note: Respect privacy and extract only public information.

Example Output:
• Profile: [username]
• Bio: [description]
• Followers: [count]
• Recent Activity: [summary]
""",
        
        'GENERAL': """
🔍 GENERAL CONTENT EXTRACTION MODE ACTIVATED

This website doesn't fit specific categories. Extract:

1. PAGE OVERVIEW:
   - Main heading/title
   - Page purpose/topic
   - Primary content sections

2. KEY INFORMATION:
   - Important facts
   - Main points
   - Relevant details

3. STRUCTURED DATA:
   - Any lists or tables
   - Statistics or numbers
   - Dates or deadlines

4. CALLS TO ACTION:
   - What the page wants users to do
   - Contact information
   - Next steps

Example Output:
• Title: [main heading]
• Purpose: [what this page is about]
• Key Information:
  - [Point 1]
  - [Point 2]
  - [Point 3]
• Action: [what user should do]
"""
    }
    
    @staticmethod
    def get_instructions(domain: str, key_data_types: List[str] = None) -> str:
        """
        Get domain-specific extraction instructions
        
        Args:
            domain: Detected domain type
            key_data_types: Specific data types to extract
            
        Returns:
            Formatted instruction string for LLM
        """
        # Normalize domain name
        domain_upper = domain.upper().replace('/', '_')
        
        # Get base instructions
        instructions = ExtractionStrategyGenerator.INSTRUCTIONS.get(
            domain_upper,
            ExtractionStrategyGenerator.INSTRUCTIONS['GENERAL']
        )
        
        # Add key data types if provided
        if key_data_types:
            data_list = ', '.join(key_data_types)
            instructions += "\n\nPRIORITY DATA TYPES TO EXTRACT:\n{}".format(data_list)
        
        return instructions


class QueryEnhancer:
    """
    Enhances user queries with domain-specific context
    """
    
    def __init__(self, llm):
        self.llm = llm
    
    def enhance_query(self, original_query: str, domain_info: Dict[str, Any]) -> str:
        """
        Enhance user query to be more specific for the detected domain
        
        Args:
            original_query: User's original question
            domain_info: Domain detection results
            
        Returns:
            Enhanced query string
        """
        domain = domain_info.get('domain', 'GENERAL')
        key_data = domain_info.get('key_data_types', [])
        
        try:
            enhancement_prompt = """You are a query enhancement specialist. Make this query more specific.

ORIGINAL QUERY: {}
DETECTED DOMAIN: {}
KEY DATA AVAILABLE: {}

Enhance this query to be more precise and comprehensive for the {} domain.
Add relevant keywords WITHOUT changing the user's intent.
Keep it natural and conversational.

Examples:
- Original: "What's the price?"
  Enhanced: "What is the current selling price, MRP, and any applicable discounts?"

- Original: "Tell me about this stock"
  Enhanced: "What is the current stock price, market capitalization, P/E ratio, volume, and day's high/low range?"

- Original: "What does this company do?"
  Enhanced: "What products and services does this company offer, what industry are they in, and who are their target customers?"

Return ONLY the enhanced query, nothing else.

ENHANCED QUERY:""".format(
                original_query,
                domain,
                ', '.join(key_data) if key_data else 'general information',
                domain
            )
            
            enhanced = self.llm.invoke(enhancement_prompt).content.strip()
            
            # Clean up the response
            enhanced = enhanced.replace('Enhanced Query:', '').strip()
            enhanced = enhanced.strip('"\'')
            
            logger.info("Query enhanced: {} -> {}".format(original_query, enhanced))
            
            return enhanced
            
        except Exception as e:
            logger.error("Query enhancement error: {}".format(str(e)))
            return original_query  # Return original if enhancement fails


# ============ MAIN INTEGRATION FUNCTION ============

def integrate_smart_domain_detection(
    url: str, 
    html_content: str, 
    user_prompt: str, 
    llm
) -> Dict[str, Any]:
    """
    Main integration function for smart domain detection
    
    Call this function in your agent workflow to get domain-specific context
    
    Args:
        url: Website URL
        html_content: Raw HTML content from scraping
        user_prompt: User's question/prompt
        llm: Language model instance
        
    Returns:
        Dictionary containing:
        - domain_info: Domain detection results
        - extraction_instructions: Domain-specific instructions for LLM
        - enhanced_prompt: Improved version of user's query
        - confidence: Detection confidence score
    
    Example Usage:
        smart_context = integrate_smart_domain_detection(
            url="https://example.com",
            html_content=scraped_html,
            user_prompt="What's the price?",
            llm=llm_instance
        )
        
        # Use in your QA prompt:
        qa_prompt = f'''
        {smart_context['extraction_instructions']}
        
        CONTENT: {content}
        QUESTION: {smart_context['enhanced_prompt']}
        
        ANSWER:
        '''
    """
    try:
        # Step 1: Detect domain
        detector = DomainDetector(llm)
        domain_info = detector.detect_domain(url, html_content)
        
        logger.info("="*60)
        logger.info("SMART DOMAIN DETECTION RESULTS")
        logger.info("="*60)
        logger.info("URL: {}".format(url))
        logger.info("Domain: {}".format(domain_info['domain']))
        logger.info("Confidence: {}%".format(domain_info['confidence']))
        logger.info("Strategy: {}".format(domain_info['strategy']))
        if domain_info['key_data_types']:
            logger.info("Key Data: {}".format(', '.join(domain_info['key_data_types'])))
        logger.info("="*60)
        
        # Step 2: Generate extraction instructions
        extraction_instructions = ExtractionStrategyGenerator.get_instructions(
            domain=domain_info['domain'],
            key_data_types=domain_info.get('key_data_types', [])
        )
        
        # Step 3: Enhance user query (only if confidence is high)
        enhanced_prompt = user_prompt
        if domain_info['confidence'] >= 60:
            enhancer = QueryEnhancer(llm)
            enhanced_prompt = enhancer.enhance_query(user_prompt, domain_info)
        else:
            logger.info("Low confidence - using original query")
        
        return {
            'domain_info': domain_info,
            'extraction_instructions': extraction_instructions,
            'enhanced_prompt': enhanced_prompt,
            'confidence': domain_info['confidence'],
            'domain': domain_info['domain']
        }
        
    except Exception as e:
        logger.error("Error in smart domain detection: {}".format(str(e)))
        # Return safe fallback
        return {
            'domain_info': {'domain': 'GENERAL', 'confidence': 0, 'key_data_types': []},
            'extraction_instructions': ExtractionStrategyGenerator.INSTRUCTIONS['GENERAL'],
            'enhanced_prompt': user_prompt,
            'confidence': 0,
            'domain': 'GENERAL'
        }


# ============ CONVENIENCE FUNCTIONS ============

def get_domain_name(url: str, html_content: str, llm) -> str:
    """Quick function to just get domain name"""
    detector = DomainDetector(llm)
    result = detector.detect_domain(url, html_content)
    return result['domain']


def get_extraction_strategy(domain: str, key_data: List[str] = None) -> str:
    """Quick function to get extraction instructions"""
    return ExtractionStrategyGenerator.get_instructions(domain, key_data)


# ============ TESTING UTILITY ============

def test_domain_detection(url: str, html_sample: str, llm):
    """
    Test function for domain detection
    Useful for debugging and validation
    """
    print("\n" + "="*70)
    print("TESTING DOMAIN DETECTION")
    print("="*70)
    
    result = integrate_smart_domain_detection(
        url=url,
        html_content=html_sample,
        user_prompt="What information is available on this page?",
        llm=llm
    )
    
    print("\nDETECTION RESULTS:")
    print("  Domain: {}".format(result['domain']))
    print("  Confidence: {}%".format(result['confidence']))
    print("\nEXTRACTION STRATEGY:")
    print("  {}".format(result['domain_info']['strategy']))
    print("\nKEY DATA TYPES:")
    for dt in result['domain_info']['key_data_types']:
        print("  - {}".format(dt))
    
    print("\n" + "="*70)
    
    return result