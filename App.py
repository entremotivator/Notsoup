import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from supabase import create_client, Client
import time
import hashlib
import jwt
from typing import Optional, Dict, Any, List
import re

# Page configuration
st.set_page_config(
    page_title="WordPress Authentication Manager",
    page_icon="🔐",
    layout="wide",
    initial_sidebar_state="expanded"
)

class WordPressAuthManager:
    def __init__(self):
        self.supabase_client = None
        self.wp_base_url = None
        self.consumer_secret = None
        self.authenticated_user = None
        
    def init_supabase(self, url: str, anon_key: str) -> bool:
        """Initialize Supabase client with proper validation"""
        try:
            # Validate URL format
            if not url or not url.startswith(('http://', 'https://')):
                st.error("❌ Invalid Supabase URL format. Must start with http:// or https://")
                return False
                
            if 'supabase' not in url.lower():
                st.error("❌ URL must contain 'supabase' in the domain")
                return False
                
            # Validate anon key
            if not anon_key or len(anon_key) < 20:
                st.error("❌ Invalid anon key. Must be at least 20 characters")
                return False
                
            # Create client
            self.supabase_client = create_client(url, anon_key)
            
            # Test connection
            response = self.supabase_client.table('wp_users').select('id').limit(1).execute()
            st.success("✅ Successfully connected to Supabase!")
            return True
            
        except Exception as e:
            st.error(f"❌ Failed to connect to Supabase: {str(e)}")
            self.supabase_client = None
            return False
    
    def create_required_tables(self) -> bool:
        """Create all required database tables"""
        if not self.supabase_client:
            st.error("❌ No Supabase connection available")
            return False
            
        tables_sql = """
        -- Create wp_users table
        CREATE TABLE IF NOT EXISTS wp_users (
            id SERIAL PRIMARY KEY,
            user_id INTEGER UNIQUE NOT NULL,
            username VARCHAR(255) NOT NULL,
            email VARCHAR(255),
            role VARCHAR(100) DEFAULT 'subscriber',
            subscription_id VARCHAR(255),
            status VARCHAR(50) DEFAULT 'active',
            product_name VARCHAR(255),
            next_payment_date DATE,
            last_sync TIMESTAMP DEFAULT NOW(),
            consumer_secret TEXT,
            wp_site_url TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- Create property_watchlist table
        CREATE TABLE IF NOT EXISTS property_watchlist (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES wp_users(id) ON DELETE CASCADE,
            property_id VARCHAR(255) NOT NULL,
            property_data JSONB,
            added_date TIMESTAMP DEFAULT NOW(),
            address TEXT,
            price DECIMAL(15,2),
            status VARCHAR(50) DEFAULT 'active',
            consumer_secret TEXT
        );

        -- Create analysis_reports table
        CREATE TABLE IF NOT EXISTS analysis_reports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES wp_users(id) ON DELETE CASCADE,
            report_data JSONB NOT NULL,
            created_date TIMESTAMP DEFAULT NOW(),
            report_type VARCHAR(100),
            property_address TEXT,
            consumer_secret TEXT
        );

        -- Create auth_sessions table
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES wp_users(id) ON DELETE CASCADE,
            session_token VARCHAR(500) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            consumer_secret TEXT,
            ip_address INET,
            user_agent TEXT
        );

        -- Create user_usage table
        CREATE TABLE IF NOT EXISTS user_usage (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES wp_users(id) ON DELETE CASCADE,
            month VARCHAR(7) NOT NULL,
            usage_count INTEGER DEFAULT 0,
            usage_type VARCHAR(100),
            last_used TIMESTAMP DEFAULT NOW(),
            consumer_secret TEXT
        );

        -- Create property_searches table
        CREATE TABLE IF NOT EXISTS property_searches (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES wp_users(id) ON DELETE CASCADE,
            property_data JSONB,
            search_date TIMESTAMP DEFAULT NOW(),
            search_type VARCHAR(100),
            address TEXT,
            property_type VARCHAR(100),
            price DECIMAL(15,2),
            bedrooms INTEGER,
            bathrooms DECIMAL(3,1),
            square_footage INTEGER,
            consumer_secret TEXT
        );
        """
        
        try:
            # Execute table creation
            self.supabase_client.rpc('exec_sql', {'sql': tables_sql}).execute()
            st.success("✅ All database tables created successfully!")
            return True
        except Exception as e:
            st.warning(f"⚠️ Could not create tables automatically: {str(e)}")
            st.info("📝 Please run the SQL manually in your Supabase SQL Editor")
            with st.expander("📋 SQL to run manually"):
                st.code(tables_sql, language='sql')
            return False
    
    def check_tables_exist(self) -> Dict[str, bool]:
        """Check which tables exist in the database"""
        required_tables = [
            'wp_users', 'property_watchlist', 'analysis_reports', 
            'auth_sessions', 'user_usage', 'property_searches'
        ]
        
        table_status = {}
        
        if not self.supabase_client:
            return {table: False for table in required_tables}
        
        for table in required_tables:
            try:
                self.supabase_client.table(table).select('*').limit(1).execute()
                table_status[table] = True
            except Exception:
                table_status[table] = False
                
        return table_status
    
    def authenticate_wordpress(self, base_url: str, consumer_secret: str) -> Dict[str, Any]:
        """Authenticate with WordPress subscription API"""
        try:
            # Clean and validate URL
            if not base_url.startswith(('http://', 'https://')):
                base_url = f"https://{base_url}"
            
            if base_url.endswith('/'):
                base_url = base_url.rstrip('/')
            
            # Construct API endpoint
            api_url = f"{base_url}/wp-json/wsp-route/v1/wsp-view-subscription"
            
            # Make API request
            response = requests.get(
                api_url,
                params={'consumer_secret': consumer_secret},
                timeout=30,
                headers={'User-Agent': 'WordPress-Auth-Manager/1.0'}
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Check for successful response
                if data.get('code') == 200 and data.get('status') == 'success':
                    subscription_data = data.get('data', {})
                    
                    # Store authentication details
                    self.wp_base_url = base_url
                    self.consumer_secret = consumer_secret
                    self.authenticated_user = subscription_data
                    
                    return {
                        'success': True,
                        'data': subscription_data,
                        'message': 'Authentication successful'
                    }
                else:
                    return {
                        'success': False,
                        'message': data.get('message', 'Authentication failed'),
                        'data': None
                    }
            else:
                return {
                    'success': False,
                    'message': f'HTTP {response.status_code}: {response.text}',
                    'data': None
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'message': 'Request timeout. Please check your internet connection.',
                'data': None
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'message': 'Connection error. Please check the WordPress URL.',
                'data': None
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'Authentication error: {str(e)}',
                'data': None
            }
    
    def sync_user_to_supabase(self, user_data: Dict[str, Any]) -> bool:
        """Sync authenticated user data to Supabase"""
        if not self.supabase_client or not user_data:
            return False
            
        try:
            # Prepare user data for database
            db_user_data = {
                'user_id': int(user_data.get('subscription_id', 0)),
                'username': user_data.get('user_name', 'Unknown'),
                'subscription_id': str(user_data.get('subscription_id', '')),
                'status': user_data.get('status', 'active'),
                'product_name': user_data.get('product_name', ''),
                'next_payment_date': user_data.get('next_payment_date'),
                'consumer_secret': self.consumer_secret,
                'wp_site_url': self.wp_base_url,
                'last_sync': datetime.now().isoformat()
            }
            
            # Handle date conversion
            if db_user_data['next_payment_date'] == '—':
                db_user_data['next_payment_date'] = None
            
            # Upsert user data
            result = self.supabase_client.table('wp_users').upsert(
                db_user_data,
                on_conflict='user_id'
            ).execute()
            
            return True
            
        except Exception as e:
            st.error(f"❌ Failed to sync user data: {str(e)}")
            return False
    
    def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """Get user statistics from database"""
        if not self.supabase_client:
            return {}
            
        try:
            # Get watchlist count
            watchlist_count = len(
                self.supabase_client.table('property_watchlist')
                .select('id')
                .eq('user_id', user_id)
                .execute().data
            )
            
            # Get reports count
            reports_count = len(
                self.supabase_client.table('analysis_reports')
                .select('id')
                .eq('user_id', user_id)
                .execute().data
            )
            
            # Get searches count
            searches_count = len(
                self.supabase_client.table('property_searches')
                .select('id')
                .eq('user_id', user_id)
                .execute().data
            )
            
            return {
                'watchlist_count': watchlist_count,
                'reports_count': reports_count,
                'searches_count': searches_count
            }
            
        except Exception as e:
            st.error(f"❌ Error getting user stats: {str(e)}")
            return {}

def main():
    st.title("🔐 WordPress Authentication Manager")
    st.markdown("---")
    
    # Initialize manager
    if 'auth_manager' not in st.session_state:
        st.session_state.auth_manager = WordPressAuthManager()
    
    manager = st.session_state.auth_manager
    
    # Sidebar for Supabase configuration
    with st.sidebar:
        st.header("🗄️ Supabase Configuration")
        
        supabase_url = st.text_input(
            "Supabase URL",
            placeholder="https://your-project.supabase.co",
            help="Your Supabase project URL"
        )
        
        supabase_anon_key = st.text_input(
            "Supabase Anon Key",
            type="password",
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            help="Your Supabase anonymous key"
        )
        
        if st.button("🔗 Connect to Supabase", type="primary"):
            if supabase_url and supabase_anon_key:
                manager.init_supabase(supabase_url, supabase_anon_key)
            else:
                st.error("❌ Please provide both URL and anon key")
        
        # Database setup section
        if manager.supabase_client:
            st.markdown("---")
            st.header("🛠️ Database Setup")
            
            # Check table status
            table_status = manager.check_tables_exist()
            missing_tables = [table for table, exists in table_status.items() if not exists]
            
            if missing_tables:
                st.warning(f"⚠️ Missing tables: {', '.join(missing_tables)}")
                if st.button("🔧 Create Missing Tables"):
                    manager.create_required_tables()
            else:
                st.success("✅ All required tables exist")
        
        # Consumer Secret for WordPress API
        st.markdown("---")
        st.header("🔑 WordPress API")
        consumer_secret = st.text_input(
            "Consumer Secret",
            type="password",
            placeholder="Enter your consumer secret",
            help="Required for WordPress subscription API"
        )
    
    # Main content area
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("🌐 WordPress Authentication")
        
        # WordPress login form
        with st.form("wordpress_login"):
            wp_url = st.text_input(
                "WordPress Site URL",
                placeholder="https://aipropiq.com",
                help="Your WordPress site URL"
            )
            
            submitted = st.form_submit_button("🔐 Authenticate", type="primary")
            
            if submitted:
                if wp_url and consumer_secret:
                    with st.spinner("🔄 Authenticating..."):
                        result = manager.authenticate_wordpress(wp_url, consumer_secret)
                        
                        if result['success']:
                            st.success("✅ Authentication successful!")
                            
                            # Display user info
                            user_data = result['data']
                            st.json(user_data)
                            
                            # Sync to Supabase if connected
                            if manager.supabase_client:
                                if manager.sync_user_to_supabase(user_data):
                                    st.success("✅ User data synced to Supabase")
                                    
                                    # Show user stats
                                    user_id = int(user_data.get('subscription_id', 0))
                                    stats = manager.get_user_stats(user_id)
                                    
                                    if stats:
                                        st.markdown("### 📊 User Statistics")
                                        col_a, col_b, col_c = st.columns(3)
                                        with col_a:
                                            st.metric("Watchlist Items", stats.get('watchlist_count', 0))
                                        with col_b:
                                            st.metric("Reports", stats.get('reports_count', 0))
                                        with col_c:
                                            st.metric("Searches", stats.get('searches_count', 0))
                        else:
                            st.error(f"❌ {result['message']}")
                else:
                    st.error("❌ Please provide both WordPress URL and Consumer Secret")
    
    with col2:
        st.header("ℹ️ Connection Status")
        
        # Supabase status
        if manager.supabase_client:
            st.success("🟢 Supabase Connected")
        else:
            st.error("🔴 Supabase Disconnected")
        
        # WordPress status
        if manager.authenticated_user:
            st.success("🟢 WordPress Authenticated")
            st.json({
                'user': manager.authenticated_user.get('user_name', 'Unknown'),
                'status': manager.authenticated_user.get('status', 'Unknown'),
                'product': manager.authenticated_user.get('product_name', 'Unknown')
            })
        else:
            st.error("🔴 WordPress Not Authenticated")
        
        # Quick actions
        if manager.authenticated_user:
            st.markdown("---")
            st.header("⚡ Quick Actions")
            
            if st.button("🔄 Refresh Data"):
                if manager.wp_base_url and manager.consumer_secret:
                    result = manager.authenticate_wordpress(manager.wp_base_url, manager.consumer_secret)
                    if result['success']:
                        st.success("✅ Data refreshed")
                        st.rerun()
            
            if st.button("🚪 Logout"):
                manager.authenticated_user = None
                manager.wp_base_url = None
                manager.consumer_secret = None
                st.success("✅ Logged out")
                st.rerun()

if __name__ == "__main__":
    main()
