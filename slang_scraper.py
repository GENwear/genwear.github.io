#!/usr/bin/env python3
"""
GENwear Slang Scraper - Enhanced Version with Targeted Research
Features:
- Original discovery mode (Reddit + Urban Dictionary)
- NEW: Targeted research mode for specific terms
- NEW: Bulk term research for dashboard integration
- NEW: Research progress tracking
- NEW: Term caching to avoid duplicate lookups
- NEW: Enhanced validation and categorization
"""

import sys
import os
import requests
import json
import time
import re
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Set
import hashlib

# Fix import path - use models.py in root directory
from models import SlangDatabase

# Urban Dictionary - Try multiple approaches
try:
    from pyurbandict import UrbanDict
    URBAN_DICT_AVAILABLE = True
    URBAN_DICT_METHOD = 'pyurbandict'
    define = None  # Not used in this method
    print("✅ pyurbandict library loaded")
except ImportError:
    UrbanDict = None  # Set to None if not available
    try:
        from urbandictionary import define
        URBAN_DICT_AVAILABLE = True
        URBAN_DICT_METHOD = 'urbandictionary'
        print("✅ urbandictionary library loaded")
    except ImportError:
        print("⚠️ Urban Dictionary not available - install with: pip install python-urbandict")
        URBAN_DICT_AVAILABLE = False
        URBAN_DICT_METHOD = None
        define = None

# OpenAI - Optional
try:
    import openai
    from openai import OpenAI
    OPENAI_AVAILABLE = True
    print("✅ OpenAI library available")
except ImportError:
    print("ℹ️ OpenAI library not found (optional)")
    openai = None
    OpenAI = None
    OPENAI_AVAILABLE = False

class SlangScraper:
    """
    Enhanced multi-platform slang scraper
    Supports both discovery mode and targeted research mode
    """
    
    def __init__(self, enable_caching: bool = True):
        self.db = SlangDatabase()
        self.session = requests.Session()
        self.enable_caching = enable_caching
        
        # NEW: Simple in-memory cache to avoid duplicate Urban Dictionary lookups
        self.urban_dict_cache = {}
        self.cache_max_age = timedelta(hours=24)  # Cache for 24 hours
        
        # Rotate user agents to avoid blocking
        self.user_agents = [
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        ]
        
        # Platform configurations
        self.reddit_config = {
            'base_url': 'https://www.reddit.com',
            'subreddits': ['teenagers', 'GenZ', 'streetwear', 'fashion', 'TikTokCringe', 'dankmemes', 'memes'],
            'user_agent': 'SlangTracker/1.0 (Educational Research)'
        }
        
        # Core slang terms we know are valid
        self.confirmed_slang = {
            # Gen Alpha (2020+)
            'rizz', 'bussin', 'no cap', 'periodt', 'slay', 'bet', 'fr', 'ngl', 
            'lowkey', 'highkey', 'mid', 'W', 'L', 'sus', 'skibidi', 'gyat', 'ohio',
            'fanum tax', 'sigma', 'mewing', 'delulu', 'cap', 'goofy ahh',
            
            # Gen Z (2010-2020) 
            'vibe', 'mood', 'based', 'cringe', 'slaps', 'hits different', 
            'stan', 'flex', 'drip', 'fire', 'ratio', 'simp', 'main character',
            
            # Fashion-specific
            'fit', 'outfit', 'clean', 'fresh', 'hard', 'sick', 'wdywt', 'ootd',
            'drip check', 'lewk', 'serving looks', 'snatched', 'on fleek'
        }
        
        # NEW: Enhanced Gen Alpha terms (based on your missing terms list)
        self.gen_alpha_terms = {
            'skibidi', 'gyat', 'ohio', 'fanum tax', 'npc', 'goofy ahh', 'sigma',
            'kai cenat', 'speed moments', 'sus', 'mewing', 'skrrt', 'nahhhh',
            'womp womp', 'bruh sound effect', 'giga chad', 'gyatt damn', 'delulu',
            'kairos', 'capybara'
        }
        
        # Slang detection patterns
        self.slang_patterns = {
            'quoted': r'"([^"]{2,20})"',
            'definition': r'(?:means?|basically|like|is when)\s+([a-zA-Z]{2,15})',
            'social_indicators': r'([a-zA-Z]{3,15})\s+(?:🔥|👀|fr|ngl|lowkey|highkey|slaps|hits different)',
            'new_term': r'(?:new|trending|fresh)\s+(?:word|term|slang)\s+([a-zA-Z]{3,15})',
            'explanation': r'([a-zA-Z]{3,15})\s+(?:means|is)\s+'
        }
        
        # Blacklisted common words
        self.blacklist = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'was', 'one', 
            'get', 'has', 'him', 'his', 'how', 'now', 'see', 'way', 'who', 'did', 'this',
            'that', 'with', 'have', 'from', 'they', 'know', 'been', 'good', 'time', 'when',
            'come', 'just', 'like', 'make', 'take', 'well', 'what', 'why', 'which', 'going',
            'today', 'where', 'about', 'other', 'really', 'there', 'could', 'would', 'should',
            'still', 'being', 'never', 'always', 'maybe', 'house', 'school', 'work', 'people',
            'reddit', 'comment', 'thread', 'upvote', 'post', 'everyone', 'something', 'anything'
        }

        # Fashion whitelist - always include these
        self.fashion_whitelist = {
            'wdywt', 'ootd', 'nyfw', 'fits', 'drip', 'slay', 'fire', 'clean', 'fresh', 
            'sick', 'hard', 'fit', 'outfit', 'rizz', 'bussin', 'periodt', 'vibe', 'mood', 
            'sus', 'based', 'cringe', 'slaps', 'lowkey', 'highkey', 'mid', 'no cap', 'bet', 
            'fr', 'ngl', 'hits different', 'W', 'L', 'stan', 'flex', 'finsta', 'vsco', 'aesthetic'
        }
        
        # NEW: Category mapping for better organization
        self.category_mapping = {
            'attitude': ['vibe', 'mood', 'slay', 'periodt', 'fire', 'based', 'cringe'],
            'fashion': ['drip', 'fit', 'outfit', 'clean', 'fresh', 'sick', 'hard', 'wdywt', 'ootd'],
            'social': ['rizz', 'sus', 'stan', 'flex', 'ratio', 'simp', 'main character'],
            'general': ['bussin', 'bet', 'fr', 'ngl', 'lowkey', 'highkey', 'mid', 'W', 'L'],
            'gen_alpha': list(self.gen_alpha_terms)
        }
    
    def get_random_headers(self):
        """Get randomized headers to avoid detection"""
        return {
            'User-Agent': random.choice(self.user_agents),
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
    
    def _get_cache_key(self, term: str) -> str:
        """Generate cache key for term"""
        return hashlib.md5(term.lower().strip().encode()).hexdigest()
    
    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid"""
        if not self.enable_caching:
            return False
        
        cached_time = datetime.fromisoformat(cache_entry['timestamp'])
        return datetime.now() - cached_time < self.cache_max_age
    
    def get_urban_definition(self, term: str, use_cache: bool = True) -> Dict:
        """
        Get Urban Dictionary definition for a term with caching
        Returns: {'found': bool, 'definition': str, 'example': str, 'votes': int, 'source': str}
        """
        if not URBAN_DICT_AVAILABLE:
            return {'found': False, 'definition': '', 'example': '', 'votes': 0, 'source': 'unavailable'}
        
        # Check cache first
        cache_key = self._get_cache_key(term)
        if use_cache and cache_key in self.urban_dict_cache:
            cache_entry = self.urban_dict_cache[cache_key]
            if self._is_cache_valid(cache_entry):
                print(f"  📋 Using cached definition for '{term}'")
                return cache_entry['data']
        
        try:
            result = {'found': False, 'definition': '', 'example': '', 'votes': 0, 'source': 'urban_dictionary'}
            if URBAN_DICT_METHOD == 'pyurbandict' and UrbanDict is not None:
                # Using pyurbandict
                ud = UrbanDict(term)
                results = ud.search()
                results = ud.search()
                
                if results:
                    top_result = results[0]
                    result.update({
                        'found': True,
                        'definition': top_result.definition[:300],  # Increased length
                        'example': top_result.example[:200] if top_result.example else '',
                        'votes': getattr(top_result, 'upvotes', 0) - getattr(top_result, 'downvotes', 0)
                    })
                        
            elif URBAN_DICT_METHOD == 'urbandictionary' and define is not None:
                # Using urbandictionary
                definitions = define(term)
                if definitions:
                    top_result = definitions[0]
                    result.update({
                        'found': True,
                        'definition': top_result.definition[:300],
                        'example': top_result.example[:200] if hasattr(top_result, 'example') and top_result.example else '',
                        'votes': getattr(top_result, 'upvotes', 0) - getattr(top_result, 'downvotes', 0)
                    })
            
            # Cache the result
            if use_cache:
                self.urban_dict_cache[cache_key] = {
                    'data': result,
                    'timestamp': datetime.now().isoformat()
                }
            
            return result
            
        except Exception as e:
            print(f"Urban Dictionary error for '{term}': {e}")
            return {'found': False, 'definition': '', 'example': '', 'votes': 0, 'source': 'error'}
    
    def categorize_term(self, term: str) -> str:
        """NEW: Automatically categorize a term based on known patterns"""
        term_lower = term.lower()
        
        for category, terms in self.category_mapping.items():
            if term_lower in terms:
                return category
        
        # Default categorization logic
        if term_lower in self.gen_alpha_terms:
            return 'gen_alpha'
        elif term_lower in self.fashion_whitelist:
            return 'fashion'
        elif any(word in term_lower for word in ['fit', 'style', 'wear', 'look']):
            return 'fashion'
        else:
            return 'general'
    
    def is_valid_slang(self, term: str, check_urban: bool = True) -> bool:
        """
        Enhanced validation with better Gen Alpha support
        """
        term = term.lower().strip()
        
        # Must be valid format
        if (not term or 
            len(term) < 2 or 
            len(term) > 20 or  # Increased max length for compound terms
            not re.match(r'^[a-zA-Z\s\-\']+$', term)):  # Allow spaces, hyphens, apostrophes
            return False
        
        # Always reject common words
        if term in self.blacklist:
            return False
        
        # Always accept whitelisted terms
        if term in self.fashion_whitelist or term in self.confirmed_slang or term in self.gen_alpha_terms:
            return True
            
        # For unknown terms, check Urban Dictionary if requested
        if check_urban and URBAN_DICT_AVAILABLE:
            ud_result = self.get_urban_definition(term)
            # More lenient threshold for Gen Alpha terms
            return ud_result['found'] and ud_result['votes'] >= -5  # Allow some negative votes
        
        # Without Urban Dictionary, be conservative but allow confirmed patterns
        return len(term) >= 3 and not term.isdigit()
    
    def research_specific_terms(self, terms_list: List[str], progress_callback=None) -> Dict:
        """
        NEW: Research specific terms using Urban Dictionary
        This is the core feature for bulk lookup integration
        """
        print(f"🔍 Researching {len(terms_list)} specific terms...")
        
        results = {
            'found_terms': [],
            'missing_terms': [],
            'error_terms': [],
            'total_processed': 0,
            'source': 'targeted_research'
        }
        
        for i, term in enumerate(terms_list):
            term_clean = term.strip().lower()
            
            # Progress callback for UI updates
            if progress_callback:
                progress_callback(i + 1, len(terms_list), term)
            
            print(f"  🔍 Researching '{term_clean}' ({i+1}/{len(terms_list)})")
            
            try:
                # Get Urban Dictionary definition
                ud_result = self.get_urban_definition(term_clean)
                
                if ud_result['found']:
                    # Determine category
                    category = self.categorize_term(term_clean)
                    
                    # Add to database
                    self.db.add_term(term_clean, ud_result['definition'], category)
                    
                    # Mark as researched (not scraped)
                    self.db.add_mention(
                        term_clean,
                        'urban_dictionary_research',
                        f"Targeted research: {ud_result['definition'][:100]}",
                        max(ud_result['votes'], 1)
                    )
                    
                    results['found_terms'].append({
                        'term': term_clean,
                        'definition': ud_result['definition'],
                        'example': ud_result['example'],
                        'category': category,
                        'votes': ud_result['votes'],
                        'source': 'urban_dictionary'
                    })
                    
                    print(f"    ✅ Found: {ud_result['definition'][:60]}...")
                else:
                    results['missing_terms'].append(term_clean)
                    print(f"    ❌ Not found in Urban Dictionary")
                
                # Rate limiting
                time.sleep(0.5)
                
            except Exception as e:
                print(f"    💥 Error researching '{term_clean}': {e}")
                results['error_terms'].append({'term': term_clean, 'error': str(e)})
            
            results['total_processed'] += 1
        
        print(f"\n📊 Research Summary:")
        print(f"   ✅ Found: {len(results['found_terms'])}")
        print(f"   ❌ Missing: {len(results['missing_terms'])}")
        print(f"   💥 Errors: {len(results['error_terms'])}")
        
        return results
    
    def batch_approve_researched_terms(self, terms_list: List[str]) -> Dict:
        """
        NEW: Batch approve terms that were successfully researched
        """
        approved_count = 0
        for term in terms_list:
            try:
                self.db.approve_term(term)
                approved_count += 1
            except Exception as e:
                print(f"Error approving {term}: {e}")
        
        return {
            'approved_count': approved_count,
            'total_requested': len(terms_list)
        }
    
    def get_research_suggestions(self, limit: int = 20) -> List[str]:
        """
        NEW: Get suggested terms to research based on patterns and missing common slang
        """
        suggestions = []
        
        # Add Gen Alpha terms that might be missing
        suggestions.extend(list(self.gen_alpha_terms))
        
        # Add other trending terms we know about
        trending_terms = [
            'no cap', 'periodt', 'hits different', 'main character', 'it girl',
            'serve', 'understood the assignment', 'living rent free', 'the way',
            'not me', 'besties', 'chile', 'purr', 'oop', 'and i oop',
            'vsco girl', 'soft girl', 'dark academia', 'cottagecore', 'y2k'
        ]
        suggestions.extend(trending_terms)
        
        # Remove duplicates and limit
        unique_suggestions = list(set(suggestions))[:limit]
        
        return unique_suggestions
    
    # Original methods remain unchanged...
    def scrape_reddit_subreddit(self, subreddit: str, sort: str = 'hot', limit: int = 50) -> List[Dict]:
        """Scrape posts from a specific subreddit"""
        url = f"{self.reddit_config['base_url']}/r/{subreddit}/{sort}.json"
        headers = self.get_random_headers()
        headers['User-Agent'] = self.reddit_config['user_agent']
        
        params = {'limit': limit}
        
        try:
            response = self.session.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            posts = data['data']['children']
            
            collected_posts = []
            for post in posts:
                post_data = post['data']
                
                collected_posts.append({
                    'id': post_data['id'],
                    'title': post_data['title'],
                    'text': post_data.get('selftext', ''),
                    'score': post_data['score'],
                    'num_comments': post_data['num_comments'],
                    'created_utc': post_data['created_utc'],
                    'author': post_data.get('author', '[deleted]'),
                    'subreddit': post_data['subreddit'],
                    'url': post_data['url'],
                    'permalink': post_data['permalink']
                })
            
            print(f"✅ Scraped {len(collected_posts)} posts from r/{subreddit}")
            return collected_posts
            
        except requests.RequestException as e:
            print(f"❌ Error scraping r/{subreddit}: {e}")
            return []
        except json.JSONDecodeError as e:
            print(f"❌ JSON error from r/{subreddit}: {e}")
            return []
    
    def extract_slang_candidates(self, text: str, source_platform: str = 'unknown') -> List[Dict]:
        """Extract potential slang terms from text"""
        if not text or len(text.strip()) < 3:
            return []
        
        candidates = []
        text_lower = text.lower()
        
        # First check for whitelisted fashion terms (always include these)
        for fashion_term in self.fashion_whitelist:
            if fashion_term in text_lower:
                candidates.append({
                    'term': fashion_term,
                    'context': text[:200],
                    'pattern': 'fashion_whitelist',
                    'confidence': 0.9,
                    'source_platform': source_platform
                })
        
        # Check for Gen Alpha terms
        for gen_alpha_term in self.gen_alpha_terms:
            if gen_alpha_term in text_lower:
                candidates.append({
                    'term': gen_alpha_term,
                    'context': text[:200],
                    'pattern': 'gen_alpha_confirmed',
                    'confidence': 0.95,
                    'source_platform': source_platform
                })
        
        # Apply slang detection patterns
        for pattern_name, pattern in self.slang_patterns.items():
            matches = re.findall(pattern, text_lower)
            
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                
                term = match.strip().lower()
                
                # Basic filtering
                if (term in self.blacklist or 
                    len(term) < 3 or 
                    len(term) > 15 or
                    term.isdigit() or
                    not term.replace(' ', '').replace('-', '').isalpha() or
                    term in [c['term'] for c in candidates]):
                    continue
                
                # Validate if it's actually slang
                if self.is_valid_slang(term):
                    base_confidence = 0.7 if pattern_name == 'definition' else 0.5
                    
                    candidates.append({
                        'term': term,
                        'context': text[:200],
                        'pattern': pattern_name,
                        'confidence': base_confidence,
                        'source_platform': source_platform
                    })
        
        # Remove duplicates and return top candidates
        seen_terms = set()
        unique_candidates = []
        
        for candidate in sorted(candidates, key=lambda x: x['confidence'], reverse=True):
            if candidate['term'] not in seen_terms:
                seen_terms.add(candidate['term'])
                unique_candidates.append(candidate)
        
        return unique_candidates[:10]  # Increased to top 10 candidates
    
    def scrape_urban_dictionary_popular_terms(self) -> List[Dict]:
        """Scrape Urban Dictionary for popular slang terms"""
        if not URBAN_DICT_AVAILABLE:
            print("❌ Urban Dictionary not available, skipping")
            return []
        
        # Enhanced popular terms list including Gen Alpha
        popular_terms = [
            'rizz', 'bussin', 'no cap', 'bet', 'periodt', 'slay', 'fire', 'drip', 'vibe', 'mood',
            'sus', 'based', 'cringe', 'slaps', 'hits different', 'lowkey', 'highkey', 'mid', 'W', 'L',
            'cap', 'fr', 'ngl', 'stan', 'flex', 'finsta', 'vsco', 'aesthetic', 'main character', 'it girl',
            'skibidi', 'gyat', 'ohio', 'fanum tax', 'sigma', 'goofy ahh', 'delulu', 'mewing'
        ]
        
        urban_terms = []
        
        for term in popular_terms:
            try:
                ud_result = self.get_urban_definition(term)
                
                if ud_result['found']:
                    urban_terms.append({
                        'term': term.lower(),
                        'definition': ud_result['definition'],
                        'example': ud_result['example'],
                        'votes': ud_result['votes'],
                        'source': 'urban_dictionary'
                    })
                    
                    print(f"  ✅ Found definition for '{term}': {ud_result['definition'][:50]}...")
                
                # Small delay between requests
                time.sleep(0.5)
                
            except Exception as e:
                print(f"  ❌ Error fetching '{term}': {e}")
                continue
        
        print(f"✅ Scraped {len(urban_terms)} terms from Urban Dictionary")
        return urban_terms
    
    def run_collection(self, reddit_posts_per_sub: int = 25) -> Dict:
        """Run complete data collection (original discovery mode)"""
        print("🎯 Starting slang collection...")
        
        results = {
            'reddit_mentions': 0,
            'urban_dictionary_terms': 0,
            'total_candidates': 0,
            'platforms_scraped': []
        }
        
        all_candidates = []
        
        # 1. Scrape Reddit
        print("\n📱 Collecting from Reddit...")
        
        for subreddit in self.reddit_config['subreddits']:
            print(f"  → Scraping r/{subreddit}...")
            
            posts = self.scrape_reddit_subreddit(subreddit, limit=reddit_posts_per_sub)
            
            for post in posts:
                # Analyze post title
                title_candidates = self.extract_slang_candidates(post['title'], 'reddit')
                for candidate in title_candidates:
                    self.db.add_mention(
                        candidate['term'],
                        'reddit',
                        f"r/{subreddit}: {post['title']}",
                        post['score']
                    )
                    all_candidates.append(candidate)
                
                # Analyze post text if available
                if post['text'] and len(post['text']) > 10:
                    text_candidates = self.extract_slang_candidates(post['text'], 'reddit')
                    for candidate in text_candidates:
                        self.db.add_mention(
                            candidate['term'],
                            'reddit',
                            f"r/{subreddit}: {post['text'][:100]}...",
                            post['score']
                        )
                        all_candidates.append(candidate)
            
            # Rate limiting
            time.sleep(random.uniform(1, 2))
        
        results['reddit_mentions'] = len(all_candidates)
        results['platforms_scraped'].append('reddit')
        
        # 2. Scrape Urban Dictionary
        if URBAN_DICT_AVAILABLE:
            print("\n📚 Collecting from Urban Dictionary...")
            urban_terms = self.scrape_urban_dictionary_popular_terms()
            
            for term_data in urban_terms:
                engagement_score = term_data['votes']
                category = self.categorize_term(term_data['term'])
                
                # Add as term if not exists
                try:
                    self.db.add_term(term_data['term'], term_data['definition'], category)
                except:
                    pass  # Term might already exist
                
                self.db.add_mention(
                    term_data['term'],
                    'urban_dictionary',
                    f"{term_data['definition']} | Example: {term_data['example']}",
                    max(engagement_score, 1)
                )
            
            results['urban_dictionary_terms'] = len(urban_terms)
            results['platforms_scraped'].append('urban_dictionary')
        
        # 3. Calculate totals
        unique_terms = set(c['term'] for c in all_candidates)
        results['total_candidates'] = len(unique_terms)
        
        print(f"\n✅ Collection complete!")
        print(f"   📊 Reddit mentions: {results['reddit_mentions']}")
        print(f"   📚 Urban Dictionary terms: {results['urban_dictionary_terms']}")
        print(f"   🎯 Total unique candidates: {results['total_candidates']}")
        print(f"   🌐 Platforms: {', '.join(results['platforms_scraped'])}")
        print(f"\n🌍 Check dashboard: http://localhost:5001")
        
        return results

def research_terms_from_list(terms_string: str) -> Dict:
    """
    NEW: Standalone function to research terms from a string
    Used by dashboard API
    """
    # Parse terms from string (handle both comma-separated and newline-separated)
    import re
    terms = re.split(r'[,\n]+', terms_string.strip())
    terms = [term.strip() for term in terms if term.strip()]
    
    scraper = SlangScraper()
    return scraper.research_specific_terms(terms)

def main():
    """
    Enhanced main function with mode selection
    """
    print("🚀 GENwear Slang Scraper - Enhanced Version")
    print("=" * 60)
    print("Features:")
    print("  🔍 Discovery Mode - Find new slang organically")
    print("  🎯 Research Mode - Look up specific terms")
    print("  📊 Dashboard Integration - Bulk term research")
    print("=" * 60)
    
    scraper = SlangScraper()
    
    if len(sys.argv) > 1:
        mode = sys.argv[1].lower()
        
        if mode == 'research' and len(sys.argv) > 2:
            # Research specific terms
            terms_to_research = sys.argv[2:]
            print(f"🔍 Research mode: Looking up {len(terms_to_research)} terms...")
            results = scraper.research_specific_terms(terms_to_research)
            
            if results['found_terms']:
                print(f"\n✅ Successfully researched {len(results['found_terms'])} terms!")
                approve = input("Approve all researched terms? (y/N): ").lower().strip()
                if approve in ['y', 'yes']:
                    found_term_names = [t['term'] for t in results['found_terms']]
                    approval_results = scraper.batch_approve_researched_terms(found_term_names)
                    print(f"✅ Approved {approval_results['approved_count']} terms")
            
        elif mode == 'suggest':
            # Show research suggestions
            suggestions = scraper.get_research_suggestions()
            print(f"\n💡 Research Suggestions ({len(suggestions)} terms):")
            for i, term in enumerate(suggestions, 1):
                print(f"  {i}. {term}")
            
        else:
            print("Usage: python slang_scraper.py [research term1 term2...] | [suggest]")
            sys.exit(1)
    else:
        # Default discovery mode
        results = scraper.run_collection()
    
    print("\n" + "=" * 60)
    print("🎉 Session completed!")
    print(f"Check your dashboard at http://localhost:5001")

if __name__ == '__main__':
    main()