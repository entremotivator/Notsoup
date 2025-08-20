import streamlit as st
import psycopg2
from supabase import create_client, Client
import time
import re

class DatabaseSetupManager:
    def __init__(self):
        self.supabase = None
        self.connection_status = False
        
    def connect_to_supabase(self, url: str, anon_key: str):
        """Connect to Supabase and test the connection"""
        try:
            if not url or not anon_key:
                return False, "URL and Anon Key are required"
                
            # Validate URL format
            if not url.startswith(('http://', 'https://')):
                return False, "URL must start with http:// or https://"
                
            if 'supabase' not in url.lower():
                return False, "URL must contain 'supabase'"
            
            self.supabase = create_client(url, anon_key)
            
            # Test connection by trying to access a system table
            result = self.supabase.table('information_schema.tables').select('table_name').limit(1).execute()
            
            if result.data is not None:
                self.connection_status = True
                return True, "Connected successfully!"
            else:
                return False, "Failed to query database"
                
        except Exception as e:
            self.connection_status = False
            return False, f"Connection failed: {str(e)}"
    
    def check_missing_tables(self):
        """Check which required tables are missing"""
        required_tables = [
            'property_watchlist', 'analysis_reports', 'auth_sessions',
            'wp_users', 'wp_subscriptions', 'user_usage', 'property_searches'
        ]
        
        if not self.supabase:
            return required_tables, "Not connected to database"
        
        try:
            # Get list of existing tables
            result = self.supabase.rpc('get_table_list').execute()
            existing_tables = [row['table_name'] for row in result.data] if result.data else []
            
            missing_tables = [table for table in required_tables if table not in existing_tables]
            return missing_tables, None
            
        except Exception as e:
            # Fallback: assume all tables are missing if we can't check
            return required_tables, f"Could not check tables: {str(e)}"
    
    def execute_sql_script(self, sql_script: str):
        """Execute the complete SQL schema script"""
        if not self.supabase:
            return False, "Not connected to database"
        
        try:
            # Extract database connection details from Supabase client
            url_parts = self.supabase.url.replace('https://', '').replace('http://', '')
            host = url_parts.split('.')[0] + '.supabase.co'
            
            # Use direct PostgreSQL connection for SQL execution
            # Note: This requires the database password
            st.warning("⚠️ Direct SQL execution requires your database password")
            password = st.text_input("Database Password", type="password", key="db_password")
            
            if not password:
                return False, "Database password required for SQL execution"
            
            # Connect directly to PostgreSQL
            conn = psycopg2.connect(
                host=host,
                database='postgres',
                user='postgres',
                password=password,
                port=5432
            )
            
            cursor = conn.cursor()
            
            # Split SQL script into individual statements
            statements = [stmt.strip() for stmt in sql_script.split(';') if stmt.strip()]
            
            progress_bar = st.progress(0)
            status_text = st.empty()
            
            for i, statement in enumerate(statements):
                if statement:
                    try:
                        status_text.text(f"Executing statement {i+1}/{len(statements)}")
                        cursor.execute(statement)
                        conn.commit()
                        progress_bar.progress((i + 1) / len(statements))
                    except Exception as stmt_error:
                        # Continue with other statements even if one fails
                        st.warning(f"Statement {i+1} failed: {str(stmt_error)}")
                        continue
            
            cursor.close()
            conn.close()
            
            status_text.text("✅ Database setup completed!")
            return True, "Database schema created successfully!"
            
        except Exception as e:
            return False, f"Failed to execute SQL: {str(e)}"

def main():
    st.set_page_config(
        page_title="Database Setup Manager",
        page_icon="🗄️",
        layout="wide"
    )
    
    st.title("🗄️ Database Setup Manager")
    st.markdown("Automatically create missing database tables and fix schema issues")
    
    # Initialize session state
    if 'setup_manager' not in st.session_state:
        st.session_state.setup_manager = DatabaseSetupManager()
    
    manager = st.session_state.setup_manager
    
    # Sidebar for Supabase connection
    with st.sidebar:
        st.header("🔗 Supabase Connection")
        
        supabase_url = st.text_input(
            "Supabase URL",
            placeholder="https://your-project.supabase.co",
            help="Your Supabase project URL"
        )
        
        anon_key = st.text_input(
            "Anon Key",
            type="password",
            placeholder="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
            help="Your Supabase anonymous key"
        )
        
        if st.button("🔌 Connect to Supabase", type="primary"):
            with st.spinner("Connecting..."):
                success, message = manager.connect_to_supabase(supabase_url, anon_key)
                if success:
                    st.success(message)
                else:
                    st.error(message)
        
        # Connection status
        if manager.connection_status:
            st.success("✅ Connected to Supabase")
        else:
            st.error("❌ Not connected")
    
    # Main content
    if manager.connection_status:
        st.success("🎉 Connected to Supabase successfully!")
        
        # Check for missing tables
        col1, col2 = st.columns([1, 1])
        
        with col1:
            st.subheader("📋 Table Status Check")
            if st.button("🔍 Check Missing Tables"):
                with st.spinner("Checking database tables..."):
                    missing_tables, error = manager.check_missing_tables()
                    
                    if error:
                        st.warning(f"⚠️ {error}")
                        st.info("Assuming all tables need to be created...")
                        missing_tables = [
                            'property_watchlist', 'analysis_reports', 'auth_sessions',
                            'wp_users', 'wp_subscriptions', 'user_usage', 'property_searches'
                        ]
                    
                    if missing_tables:
                        st.error(f"❌ Missing tables: {', '.join(missing_tables)}")
                        st.session_state.missing_tables = missing_tables
                    else:
                        st.success("✅ All required tables exist!")
                        st.session_state.missing_tables = []
        
        with col2:
            st.subheader("🛠️ Database Setup")
            
            # Show missing tables if any
            if hasattr(st.session_state, 'missing_tables') and st.session_state.missing_tables:
                st.warning(f"Missing tables: {', '.join(st.session_state.missing_tables)}")
                
                if st.button("🚀 Create All Tables", type="primary"):
                    # Complete SQL schema
                    sql_schema = """
-- Complete Database Schema
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgcrypto";

-- Create all required tables
CREATE TABLE IF NOT EXISTS property_watchlist (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    property_id BIGINT NOT NULL,
    watchlist_name VARCHAR(255) DEFAULT 'Default Watchlist',
    priority VARCHAR(20) DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high')),
    notes TEXT,
    price_alert_threshold DECIMAL(12,2),
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS analysis_reports (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL,
    property_id BIGINT,
    report_type VARCHAR(50) NOT NULL CHECK (report_type IN ('market_analysis', 'investment_analysis', 'comparative_analysis', 'rental_analysis')),
    report_title VARCHAR(255) NOT NULL,
    report_data JSONB NOT NULL,
    analysis_parameters JSONB DEFAULT '{}',
    confidence_score DECIMAL(3,2) CHECK (confidence_score >= 0 AND confidence_score <= 1),
    generated_by VARCHAR(50) DEFAULT 'system',
    status VARCHAR(20) DEFAULT 'completed' CHECK (status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    session_token VARCHAR(255) UNIQUE NOT NULL,
    wp_site_url VARCHAR(500) NOT NULL,
    auth_method VARCHAR(50) DEFAULT 'jwt',
    consumer_secret TEXT,
    expires_at TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true
);

CREATE TABLE IF NOT EXISTS wp_users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    display_name VARCHAR(255),
    wp_user_id INTEGER UNIQUE,
    consumer_key VARCHAR(255),
    consumer_secret TEXT,
    jwt_token TEXT,
    token_expires_at TIMESTAMP,
    last_sync TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    role VARCHAR(50) DEFAULT 'subscriber',
    subscription_id INTEGER,
    status VARCHAR(50) DEFAULT 'active',
    product_name VARCHAR(255),
    next_payment_date TIMESTAMP
);

CREATE TABLE IF NOT EXISTS wp_subscriptions (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    subscription_id INTEGER NOT NULL,
    parent_order_id VARCHAR(255),
    status VARCHAR(50) NOT NULL,
    product_name VARCHAR(255),
    recurring_amount DECIMAL(10,2),
    user_name VARCHAR(255),
    next_payment_date TIMESTAMP,
    subscriptions_expiry_date TIMESTAMP,
    consumer_secret TEXT NOT NULL,
    wp_site_url VARCHAR(500) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS user_usage (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    month VARCHAR(7) NOT NULL,
    usage_count INTEGER DEFAULT 0,
    usage_type VARCHAR(50) DEFAULT 'api_call',
    last_used TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS property_searches (
    id SERIAL PRIMARY KEY,
    user_id INTEGER,
    property_data JSONB NOT NULL,
    search_date TIMESTAMP DEFAULT NOW(),
    search_type VARCHAR(50) DEFAULT 'general',
    address TEXT,
    property_type VARCHAR(100),
    price DECIMAL(12,2),
    bedrooms INTEGER,
    bathrooms DECIMAL(3,1),
    square_footage INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX IF NOT EXISTS idx_property_watchlist_user_id ON property_watchlist(user_id);
CREATE INDEX IF NOT EXISTS idx_analysis_reports_user_id ON analysis_reports(user_id);
CREATE INDEX IF NOT EXISTS idx_auth_sessions_user_id ON auth_sessions(user_id);
CREATE INDEX IF NOT EXISTS idx_wp_users_username ON wp_users(username);
CREATE INDEX IF NOT EXISTS idx_wp_users_last_sync ON wp_users(last_sync);
CREATE INDEX IF NOT EXISTS idx_user_usage_user_id ON user_usage(user_id);
CREATE INDEX IF NOT EXISTS idx_property_searches_user_id ON property_searches(user_id);

-- Create sync function
CREATE OR REPLACE FUNCTION sync_user_data(
    p_user_id INTEGER,
    p_subscription_id INTEGER DEFAULT NULL,
    p_status VARCHAR(50) DEFAULT NULL,
    p_product_name VARCHAR(255) DEFAULT NULL,
    p_next_payment_date TIMESTAMP DEFAULT NULL
)
RETURNS VOID AS $$
BEGIN
    UPDATE wp_users 
    SET 
        subscription_id = COALESCE(p_subscription_id, subscription_id),
        status = COALESCE(p_status, status),
        product_name = COALESCE(p_product_name, product_name),
        next_payment_date = COALESCE(p_next_payment_date, next_payment_date),
        last_sync = NOW(),
        updated_at = NOW()
    WHERE id = p_user_id;
END;
$$ LANGUAGE plpgsql;
"""
                    
                    with st.spinner("Creating database tables..."):
                        success, message = manager.execute_sql_script(sql_schema)
                        
                        if success:
                            st.success("✅ " + message)
                            st.balloons()
                            # Clear missing tables
                            st.session_state.missing_tables = []
                        else:
                            st.error("❌ " + message)
    
    else:
        st.info("👆 Please connect to your Supabase database using the sidebar")
        
        # Show connection instructions
        with st.expander("📖 How to get your Supabase credentials"):
            st.markdown("""
            1. Go to your [Supabase Dashboard](https://app.supabase.com)
            2. Select your project
            3. Go to **Settings** → **API**
            4. Copy your **Project URL** and **anon/public key**
            5. Paste them in the sidebar and click Connect
            """)

if __name__ == "__main__":
    main()
