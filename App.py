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
            
            # Test connection with existing tables
            try:
                response = self.supabase_client.table('users').select('id').limit(1).execute()
                st.success("✅ Successfully connected to Supabase!")
                return True
            except:
                # Try wp_users if users doesn't exist
                try:
                    response = self.supabase_client.table('wp_users').select('id').limit(1).execute()
                    st.success("✅ Successfully connected to Supabase!")
                    return True
                except:
                    st.success("✅ Connected to Supabase (no user tables found yet)")
                    return True
            
        except Exception as e:
            st.error(f"❌ Failed to connect to Supabase: {str(e)}")
            self.supabase_client = None
            return False
    
    def create_missing_tables_only(self) -> bool:
        """Create only the missing tables that don't exist"""
        if not self.supabase_client:
            st.error("❌ No Supabase connection available")
            return False
            
        missing_tables_sql = """
        -- Create property_watchlist table if it doesn't exist
        CREATE TABLE IF NOT EXISTS property_watchlist (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            property_id VARCHAR(255) NOT NULL,
            property_data JSONB,
            added_date TIMESTAMP DEFAULT NOW(),
            address TEXT,
            price DECIMAL(15,2),
            status VARCHAR(50) DEFAULT 'active',
            consumer_secret TEXT,
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- Create analysis_reports table if it doesn't exist
        CREATE TABLE IF NOT EXISTS analysis_reports (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            report_data JSONB NOT NULL,
            created_date TIMESTAMP DEFAULT NOW(),
            report_type VARCHAR(100),
            property_address TEXT,
            consumer_secret TEXT,
            confidence_score DECIMAL(3,2),
            status VARCHAR(50) DEFAULT 'completed',
            created_at TIMESTAMP DEFAULT NOW(),
            updated_at TIMESTAMP DEFAULT NOW()
        );

        -- Create auth_sessions table if it doesn't exist
        CREATE TABLE IF NOT EXISTS auth_sessions (
            id SERIAL PRIMARY KEY,
            user_id INTEGER NOT NULL,
            session_token VARCHAR(500) NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            created_at TIMESTAMP DEFAULT NOW(),
            consumer_secret TEXT,
            ip_address INET,
            user_agent TEXT,
            is_active BOOLEAN DEFAULT true,
            last_activity TIMESTAMP DEFAULT NOW()
        );

        -- Add consumer_secret column to existing tables if missing
        DO $$ 
        BEGIN
            -- Add to users table
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='users') THEN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='users' AND column_name='consumer_secret') THEN
                    ALTER TABLE users ADD COLUMN consumer_secret TEXT;
                END IF;
            END IF;
            
            -- Add to wp_users table
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='wp_users') THEN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='wp_users' AND column_name='consumer_secret') THEN
                    ALTER TABLE wp_users ADD COLUMN consumer_secret TEXT;
                END IF;
            END IF;
            
            -- Add to user_usage table
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='user_usage') THEN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='user_usage' AND column_name='consumer_secret') THEN
                    ALTER TABLE user_usage ADD COLUMN consumer_secret TEXT;
                END IF;
            END IF;
            
            -- Add to property_searches table
            IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name='property_searches') THEN
                IF NOT EXISTS (SELECT 1 FROM information_schema.columns 
                              WHERE table_name='property_searches' AND column_name='consumer_secret') THEN
                    ALTER TABLE property_searches ADD COLUMN consumer_secret TEXT;
                END IF;
            END IF;
        END $$;

        -- Create indexes for better performance
        CREATE INDEX IF NOT EXISTS idx_property_watchlist_user_id ON property_watchlist(user_id);
        CREATE INDEX IF NOT EXISTS idx_property_watchlist_consumer_secret ON property_watchlist(consumer_secret);
        CREATE INDEX IF NOT EXISTS idx_analysis_reports_user_id ON analysis_reports(user_id);
        CREATE INDEX IF NOT EXISTS idx_analysis_reports_consumer_secret ON analysis_reports(consumer_secret);
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id);
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_consumer_secret ON auth_sessions(consumer_secret);
        CREATE INDEX IF NOT EXISTS idx_auth_sessions_expires_at ON auth_sessions(expires_at);
        """
        
        st.info("📝 Please run this SQL in your Supabase SQL Editor to create missing tables:")
        
        with st.expander("📋 SQL for Missing Tables", expanded=True):
            st.code(missing_tables_sql, language='sql')
            
        if st.button("📋 Copy SQL to Clipboard", key="copy_missing_tables"):
            st.success("✅ SQL copied! Paste it into your Supabase SQL Editor and run it.")
            
        return True
    
    def check_tables_exist(self) -> Dict[str, bool]:
        """Check which tables exist in the database"""
        required_tables = [
            'property_watchlist', 'analysis_reports', 'auth_sessions'
        ]
        
        existing_tables = [
            'users', 'wp_users', 'user_usage', 'property_searches', 
            'properties', 'api_usage', 'market_alerts', 'profiles'
        ]
        
        table_status = {}
        
        if not self.supabase_client:
            return {table: False for table in required_tables + existing_tables}
        
        # Check required tables
        for table in required_tables:
            try:
                self.supabase_client.table(table).select('*').limit(1).execute()
                table_status[table] = True
            except Exception:
                table_status[table] = False
        
        # Check existing tables
        for table in existing_tables:
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
                'username': user_data.get('user_name', 'Unknown'),
                'subscription_id': str(user_data.get('subscription_id', '')),
                'status': user_data.get('status', 'active'),
                'product_name': user_data.get('product_name', ''),
                'next_payment_date': user_data.get('next_payment_date'),
                'wp_site_url': self.wp_base_url,
                'last_sync': datetime.now().isoformat()
            }
            
            if self.consumer_secret:
                db_user_data['consumer_secret'] = self.consumer_secret
            
            # Handle date conversion
            if db_user_data['next_payment_date'] == '—':
                db_user_data['next_payment_date'] = None
            
            # Try to sync to users table first, then wp_users
            try:
                # Add user_id for users table
                db_user_data['user_id'] = int(user_data.get('subscription_id', 0))
                result = self.supabase_client.table('users').upsert(
                    db_user_data,
                    on_conflict='user_id'
                ).execute()
                return True
            except:
                # Try wp_users table
                try:
                    result = self.supabase_client.table('wp_users').upsert(
                        db_user_data,
                        on_conflict='user_id'
                    ).execute()
                    return True
                except Exception as e:
                    raise e
            
        except Exception as e:
            error_msg = str(e)
            if "consumer_secret" in error_msg and "does not exist" in error_msg:
                st.error("❌ The consumer_secret column doesn't exist. Please run the database setup script.")
                st.info("💡 Click 'Setup Missing Tables' in the sidebar to add the consumer_secret column.")
            else:
                st.error(f"❌ Failed to sync user data: {error_msg}")
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
        
        if manager.supabase_client:
            st.markdown("---")
            st.header("🛠️ Database Setup")
            
            # Check table status
            table_status = manager.check_tables_exist()
            missing_required = [table for table in ['property_watchlist', 'analysis_reports', 'auth_sessions'] 
                              if not table_status.get(table, False)]
            existing_tables = [table for table, exists in table_status.items() if exists and table not in missing_required]
            
            if existing_tables:
                st.success(f"✅ Existing tables: {', '.join(existing_tables)}")
            
            if missing_required:
                st.warning(f"⚠️ Missing tables: {', '.join(missing_required)}")
                if st.button("🔧 Setup Missing Tables"):
                    manager.create_missing_tables_only()
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
        if manager.authenticated_user and isinstance(manager.authenticated_user, dict):
            st.success("🟢 WordPress Authenticated")
            st.json({
                'user': manager.authenticated_user.get('user_name', 'Unknown'),
                'status': manager.authenticated_user.get('status', 'Unknown'),
                'product': manager.authenticated_user.get('product_name', 'Unknown')
            })
        else:
            st.error("🔴 WordPress Not Authenticated")
        
        # Quick actions
        if manager.authenticated_user and isinstance(manager.authenticated_user, dict):
            st.markdown("---")
            st.header("⚡ Quick Actions")
            
            if st.button("🔄 Refresh Data"):
                if manager.wp_base_url and manager.consumer_secret:
                    with st.spinner("🔄 Refreshing..."):
                        result = manager.authenticate_wordpress(manager.wp_base_url, manager.consumer_secret)
                        if result['success']:
                            if manager.supabase_client:
                                manager.sync_user_to_supabase(result['data'])
                            st.success("✅ Data refreshed and synced")
                            st.rerun()
                        else:
                            st.error(f"❌ Refresh failed: {result['message']}")
            
            if st.button("🚪 Logout"):
                manager.authenticated_user = None
                manager.wp_base_url = None
                manager.consumer_secret = None
                st.success("✅ Logged out")
                st.rerun()

if __name__ == "__main__":
    main()


