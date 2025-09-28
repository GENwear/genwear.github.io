#!/usr/bin/env python3
"""
Fixed database population script for GENwear Slang Tracker
"""

import sys
import os
from datetime import datetime, timedelta
import random

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    from models import SlangDatabase
    print("✅ Successfully imported SlangDatabase")
except ImportError as e:
    print(f"❌ Error importing SlangDatabase: {e}")
    sys.exit(1)

def populate_database():
    """Populate the database with sample slang terms"""
    
    db = SlangDatabase()
    
    # Simple terms to add
    terms_to_add = [
        ('drip', 'Fashionable, stylish clothing or accessories', 'fashion'),
        ('fit', 'An outfit or overall style of clothing', 'fashion'), 
        ('slay', 'To do something exceptionally well or look amazing', 'attitude'),
        ('mid', 'Average, mediocre, or disappointing', 'quality'),
        ('fire', 'Something that is excellent, amazing, or outstanding', 'attitude'),
        ('bussin', 'Extremely good or excellent', 'expression'),
        ('no cap', 'No lie, telling the truth', 'expression'),
        ('bet', 'Agreement, okay, or for sure', 'expression'),
        ('periodt', 'Period, end of discussion', 'expression'),
        ('vibe', 'A feeling or atmosphere', 'attitude'),
        ('aesthetic', 'A particular style or visual appearance', 'fashion'),
        ('basic', 'Mainstream or unoriginal', 'quality'),
        ('flex', 'To show off or boast', 'attitude'),
        ('sus', 'Suspicious or questionable', 'quality'),
        ('stan', 'To be a big fan of someone or something', 'social'),
        ('mood', 'Relatable feeling or situation', 'attitude'),
        ('iconic', 'Legendary or memorable', 'quality'),
        ('serve', 'To deliver excellence', 'attitude'),
        ('based', 'Being true to yourself regardless of others opinions', 'attitude'),
        ('cringe', 'Embarrassing or awkward', 'quality')
    ]
    
    # Add more terms to reach 107
    additional_terms = [
        'lowkey', 'highkey', 'deadass', 'facts', 'same', 'valid', 'legend', 
        'queen', 'king', 'ate', 'period', 'snapped', 'obsessed', 'bestie',
        'toxic', 'wholesome', 'chaos', 'ratio', 'cope', 'seethe', 'smol',
        'bean', 'baby', 'angel', 'menace', 'glow up', 'level up', 'upgrade',
        'fresh', 'clean', 'sleek', 'crisp', 'bougie', 'cheugy', 'ship',
        'say less', 'flex', 'humble flex', 'soft launch', 'hard launch',
        'slaps', 'bop', 'banger', 'main character', 'side quest', 'plot twist',
        'green flag', 'red flag', 'beige flag', 'unhinged', 'feral',
        'big mood', 'whole mood', 'sending me', 'touch grass', 'log off',
        'down bad', 'caught in 4k', 'smooth brain', 'galaxy brain', 'big brain',
        'precious', 'protect at all costs', 'demon', 'villain era', 'redemption arc',
        'evolution', 'metamorphosis', 'understood the assignment', 'go off', 'pop off',
        'came through', 'delivered', 'rent free', 'living for', 'not me', 'the way',
        'bestie behavior', 'character development', 'chaotic energy', 'whew chile',
        'chile anyway', 'not this', 'malding', 'no thoughts head empty', 'brain empty'
    ]
    
    # Combine all terms
    all_terms = []
    for term, definition, category in terms_to_add:
        all_terms.append((term, definition, category))
    
    for term in additional_terms:
        categories = ['fashion', 'attitude', 'quality', 'social', 'lifestyle', 'expression']
        all_terms.append((term, f'Popular slang term: {term}', random.choice(categories)))
    
    print(f"📝 Adding {len(all_terms)} terms to database...")
    
    success_count = 0
    
    # Try different insertion methods
    for term_name, definition, category in all_terms:
        try:
            # Method 1: Try direct insertion with individual parameters
            if hasattr(db, 'add_term'):
                try:
                    db.add_term(term_name, definition, category)
                    success_count += 1
                    continue
                except:
                    pass
            
            # Method 2: Try with more parameters
            if hasattr(db, 'insert_term'):
                try:
                    mentions = random.randint(5, 50)
                    engagement = random.uniform(30.0, 95.0)
                    first_seen = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime('%Y-%m-%d')
                    
                    db.insert_term(term_name, definition, category, mentions, engagement, first_seen, 'pending', 'gen-z')
                    success_count += 1
                    continue
                except:
                    pass
            
            # Method 3: Try execute raw SQL
            if hasattr(db, 'cursor') or hasattr(db, 'conn'):
                try:
                    mentions = random.randint(5, 50)
                    engagement = random.uniform(30.0, 95.0)
                    first_seen = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime('%Y-%m-%d')
                    
                    cursor = getattr(db, 'cursor', None) or getattr(db, 'conn', None).cursor()
                    cursor.execute("""
                        INSERT INTO slang_terms 
                        (term, definition, category, mentions, avg_engagement, first_seen, approval_status, generation)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (term_name, definition, category, mentions, engagement, first_seen, 'pending', 'gen-z'))
                    
                    if hasattr(db, 'conn'):
                        db.conn.commit()
                    success_count += 1
                    continue
                except Exception as e:
                    print(f"SQL insert failed for {term_name}: {e}")
            
            print(f"⚠️  Could not insert {term_name}")
            
        except Exception as e:
            print(f"⚠️  Error inserting {term_name}: {e}")
    
    print(f"✅ Successfully inserted {success_count} out of {len(all_terms)} terms")
    
    # Get final stats
    try:
        stats = db.get_stats()
        print(f"\n�� Final Database Stats:")
        print(f"   Total terms: {stats['total_terms']}")
        print(f"   Approved terms: {stats['approved_terms']}")
        print(f"   Pending terms: {stats['pending_terms']}")
        print(f"   Total mentions: {stats['total_mentions']}")
        
        return stats['total_terms'] > 0
    except Exception as e:
        print(f"❌ Error getting stats: {e}")
        return success_count > 0

if __name__ == '__main__':
    print("🚀 Starting database population...")
    success = populate_database()
    if success:
        print("✅ Database population completed successfully!")
    else:
        print("❌ Database population failed!")
        sys.exit(1)
