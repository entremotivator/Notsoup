"""
Enhanced RentCast Real Estate Data Lookup Application
====================================================

A comprehensive real estate data analysis platform that combines:
- WordPress subscription authentication
- RentCast API integration
- Advanced property analytics
- Investment analysis tools
- Market comparison features
- Comprehensive reporting system
- Property watchlist management
- Neighborhood analysis
- Rental yield calculations
- Property valuation tools

Author: Enhanced by AI Assistant
Version: 2.0.0
"""

import streamlit as st
import requests
import pandas as pd
import json
import numpy as np
from datetime import datetime, timedelta, date
import hashlib
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional, List, Tuple
import time
import io
import base64
from PIL import Image
import folium
from streamlit_folium import folium_static
import seaborn as sns
import matplotlib.pyplot as plt
from scipy import stats
import warnings
from supabase.lib.client_options import ClientOptions
from gotrue.errors import AuthApiError

warnings.filterwarnings('ignore')

# Page configuration
st.set_page_config(
    page_title="Enhanced RentCast Real Estate Analytics Platform",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for enhanced styling
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        background: linear-gradient(90deg, #1f77b4, #ff7f0e);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        padding: 1rem 0;
    }
    
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #2c3e50;
        margin-bottom: 1rem;
        border-bottom: 2px solid #3498db;
        padding-bottom: 0.5rem;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.2);
    }
    
    .feature-card {
        background: rgba(255,255,255,0.9);
        padding: 1.5rem;
        border-radius: 12px;
        border-left: 5px solid #e74c3c;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .investment-card {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 1rem 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .warning-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .success-card {
        background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin: 0.5rem 0;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    .stAlert > div {
        padding-top: 0.5rem;
    }
    
    .property-summary {
        background: rgba(52, 152, 219, 0.1);
        padding: 2rem;
        border-radius: 15px;
        border: 2px solid #3498db;
        margin: 1rem 0;
    }
    
    .comparison-table {
        background: white;
        border-radius: 10px;
        padding: 1rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    }
    
    .analysis-section {
        background: linear-gradient(135deg, rgba(255,255,255,0.9) 0%, rgba(240,242,246,0.9) 100%);
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        border: 1px solid rgba(52, 152, 219, 0.2);
    }
</style>
""", unsafe_allow_html=True)

class WordPressAuthManager:
    """WordPress subscription authentication manager"""
    
    def __init__(self, api_url: str = "https://aipropiq.com/wp-json/wsp-route/v1/wsp-view-subscription"):
        self.api_url = api_url
        self.admin_users = ["admin", "superadmin", "donmenico"]  # Admin whitelist
    
    def check_subscription(self, username: str, password: str, consumer_secret: str = None) -> Tuple[bool, Dict[str, Any]]:
        """Check if user has an active subscription or is admin"""
        try:
            # Prepare parameters - include consumer_secret if provided
            params = {"username": username}
            if consumer_secret:
                params["consumer_secret"] = consumer_secret
            
            # Method 1: Basic authentication with consumer_secret
            if consumer_secret:
                response = requests.get(
                    self.api_url,
                    params=params,
                    timeout=15
                )
            else:
                # Method 2: Query parameter authentication (fallback)
                params["password"] = password
                response = requests.get(
                    self.api_url,
                    params=params,
                    timeout=15
                )
            
            # Method 3: Authorization header if first methods fail
            if response.status_code == 401 or response.status_code == 403:
                auth_token = consumer_secret if consumer_secret else password
                # Ensure token has proper JWT structure (header.payload.signature)
                if auth_token and '.' not in auth_token:
                    # If not a proper JWT, try basic auth format
                    import base64
                    credentials = base64.b64encode(f"{username}:{auth_token}".encode()).decode()
                    headers = {
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/json"
                    }
                else:
                    headers = {
                        "Authorization": f"Bearer {auth_token}",
                        "Content-Type": "application/json"
                    }
                
                response = requests.get(
                    self.api_url,
                    headers=headers,
                    params={"username": username},
                    timeout=15
                )
            
            # Method 4: Custom header if other methods fail
            if response.status_code == 401 or response.status_code == 403:
                headers = {
                    "X-WP-Password": password,
                    "X-Consumer-Secret": consumer_secret if consumer_secret else "",
                    "Content-Type": "application/json"
                }
                response = requests.get(
                    self.api_url,
                    headers=headers,
                    params={"username": username},
                    timeout=15
                )
            
            if response.status_code != 200:
                error_msg = f"API error ({response.status_code}): {response.text}"
                try:
                    error_data = response.json()
                    if 'message' in error_data:
                        error_msg = f"API error ({response.status_code}): {error_data['message']}"
                except:
                    pass
                return False, {"error": error_msg}
            
            try:
                data = response.json()
            except json.JSONDecodeError:
                return False, {"error": "Invalid JSON response from API"}
            
            if data.get("status") != "success":
                return False, {"error": data.get("message", "Invalid API response")}
            
            subscriptions = data.get("data", [])
            
            # Admin access check
            if username.lower() in [admin.lower() for admin in self.admin_users]:
                return True, {
                    "role": "admin",
                    "user_name": username,
                    "status": "active",
                    "product_name": "Admin Access",
                    "message": "Admin access granted"
                }
            
            # Check for active subscription
            for sub in subscriptions:
                if (sub.get("user_name", "").lower() == username.lower() and 
                    sub.get("status") == "active"):
                    return True, {
                        "role": "subscriber",
                        **sub
                    }
            
            return False, {"error": "No active subscription found"}
        
        except requests.exceptions.Timeout:
            return False, {"error": "Request timeout - please try again"}
        except requests.exceptions.ConnectionError:
            return False, {"error": "Connection error - please check your internet connection"}
        except Exception as e:
            return False, {"error": f"Authentication error: {str(e)}"}
    
    def sync_user_data(self, supabase_manager, user_data: Dict[str, Any]) -> bool:
        """Sync WordPress user data with Supabase"""
        try:
            user_id = hashlib.md5(user_data.get("user_name", "").encode()).hexdigest()
            
            # Update or insert user data
            supabase_manager.client.table("wp_users").upsert({
                "user_id": user_id,
                "username": user_data.get("user_name"),
                "role": user_data.get("role"),
                "subscription_id": user_data.get("subscription_id"),
                "status": user_data.get("status"),
                "product_name": user_data.get("product_name"),
                "next_payment_date": user_data.get("next_payment_date"),
                "last_sync": datetime.now().isoformat()
            }).execute()
            
            return True
        except Exception as e:
            st.error(f"Failed to sync user data: {str(e)}")
            return False

class RentCastAPI:
    """Enhanced RentCast API client with comprehensive data handling"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.rentcast.io/v1"
        self.headers = {
            "accept": "application/json",
            "X-Api-Key": api_key
        }
        self.rate_limit_delay = 1  # seconds between requests
    
    def _make_request(self, endpoint: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make API request with error handling and rate limiting"""
        url = f"{self.base_url}/{endpoint}"
        
        try:
            time.sleep(self.rate_limit_delay)  # Rate limiting
            response = requests.get(url, headers=self.headers, params=params, timeout=30)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {str(e)}")
            return {}
    
    def search_properties(self, address: str) -> Dict[str, Any]:
        """Search for properties by address"""
        return self._make_request("properties", {"address": address})
    
    def get_property_details(self, property_id: str) -> Dict[str, Any]:
        """Get detailed property information"""
        return self._make_request(f"properties/{property_id}")
    
    def get_rental_estimates(self, address: str) -> Dict[str, Any]:
        """Get rental estimates for property"""
        return self._make_request("rentals", {"address": address})
    
    def get_comparable_properties(self, address: str, radius: float = 0.5) -> Dict[str, Any]:
        """Get comparable properties in the area"""
        return self._make_request("properties/comparables", {
            "address": address,
            "radius": radius,
            "limit": 20
        })
    
    def get_market_data(self, city: str, state: str) -> Dict[str, Any]:
        """Get market data for city/state"""
        return self._make_request("markets", {
            "city": city,
            "state": state
        })

class SupabaseManager:
    """Enhanced Supabase manager for comprehensive data management"""
    
    def __init__(self, url: str, key: str):
        self.client = None
        self.connection_status = False
        
        try:
            if not url or not key:
                st.warning("⚠️ Supabase URL and Anon Key are required for database functionality")
                return
            
            if not url.startswith(('http://', 'https://')):
                st.error("❌ Invalid URL format. URL must start with http:// or https://")
                return
            
            if not url.endswith('.supabase.co') and 'supabase' not in url:
                st.error("❌ Invalid Supabase URL. Please use your project's Supabase URL")
                return
                
            self.client: Client = create_client(url, key)
            
            # Test connection with better error handling
            test_response = self.client.table("wp_users").select("count", count="exact").limit(1).execute()
            self.connection_status = True
            st.success("✅ Supabase connection established successfully!")
            
        except Exception as e:
            error_msg = str(e)
            if "Invalid API key" in error_msg:
                st.error("❌ Invalid Supabase API key. Please check your credentials.")
            elif "not found" in error_msg.lower() or "Invalid URL" in error_msg:
                st.error("❌ Invalid Supabase URL. Please check your project URL format.")
            elif "Failed to establish a new connection" in error_msg:
                st.error("❌ Network connection failed. Please check your internet connection.")
            else:
                st.error(f"❌ Failed to connect to Supabase: {error_msg}")
            
            st.info("💡 Configure Supabase in the sidebar to enable database features")
            self.client = None
            self.connection_status = False
    
    def is_connected(self) -> bool:
        """Check if Supabase client is properly connected"""
        return self.client is not None and self.connection_status
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in existing user with improved error handling"""
        if not self.is_connected():
            return {"success": False, "error": "Supabase client not connected"}
        
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {"success": True, "user": response.user, "session": response.session}
        except AuthApiError as e:
            return {"success": False, "error": f"Authentication failed: {e.message}"}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def sign_out(self) -> bool:
        """Sign out current user"""
        if not self.is_connected():
            return False
        
        try:
            self.client.auth.sign_out()
            return True
        except Exception as e:
            st.error(f"Sign out error: {str(e)}")
            return False
    
    def get_current_user(self):
        """Get current authenticated user"""
        if not self.is_connected():
            return None
        
        try:
            user = self.client.auth.get_user()
            return user.user if user else None
        except Exception:
            return None
    
    def reset_password(self, email: str) -> Dict[str, Any]:
        """Send password reset email with corrected method name"""
        if not self.is_connected():
            return {"success": False, "error": "Supabase client not connected"}
        
        try:
            self.client.auth.reset_password_for_email(email)
            return {"success": True}
        except AuthApiError as e:
            return {"success": False, "error": f"Reset failed: {e.message}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def create_tables_if_not_exist(self):
        """Create necessary tables if they don't exist with automatic creation"""
        if not self.is_connected():
            st.warning("⚠️ Cannot check database tables - Supabase not connected")
            return False
        
        try:
            tables_to_check = [
                "wp_users", "user_usage", "property_searches", 
                "property_watchlist", "analysis_reports", "auth_sessions"
            ]
            
            missing_tables = []
            for table in tables_to_check:
                try:
                    self.client.table(table).select("*").limit(1).execute()
                except Exception:
                    missing_tables.append(table)
            
            if missing_tables:
                st.info(f"🔧 Creating missing tables: {', '.join(missing_tables)}")
                success = self.create_missing_tables(missing_tables)
                if success:
                    st.success("✅ All required database tables created successfully")
                    return True
                else:
                    st.error("❌ Failed to create some tables. Please check your database permissions.")
                    return False
            else:
                st.success("✅ All required database tables exist")
                return True
                
        except Exception as e:
            st.error(f"❌ Database check failed: {str(e)}")
            return False

    def create_missing_tables(self, missing_tables):
        """Create missing tables using SQL commands"""
        try:
            table_sql = {
                "wp_users": """
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
                        created_at TIMESTAMP DEFAULT NOW(),
                        updated_at TIMESTAMP DEFAULT NOW()
                    );
                """,
                "user_usage": """
                    CREATE TABLE IF NOT EXISTS user_usage (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES wp_users(user_id) ON DELETE CASCADE,
                        month VARCHAR(7) NOT NULL,
                        usage_count INTEGER DEFAULT 0,
                        usage_type VARCHAR(100) DEFAULT 'api_call',
                        last_used TIMESTAMP DEFAULT NOW(),
                        consumer_secret TEXT,
                        created_at TIMESTAMP DEFAULT NOW()
                    );
                """,
                "property_searches": """
                    CREATE TABLE IF NOT EXISTS property_searches (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES wp_users(user_id) ON DELETE CASCADE,
                        property_data JSONB,
                        search_date TIMESTAMP DEFAULT NOW(),
                        search_type VARCHAR(100) DEFAULT 'analysis',
                        address TEXT,
                        property_type VARCHAR(100),
                        price DECIMAL(15,2),
                        bedrooms INTEGER,
                        bathrooms DECIMAL(3,1),
                        square_footage INTEGER,
                        consumer_secret TEXT
                    );
                """,
                "property_watchlist": """
                    CREATE TABLE IF NOT EXISTS property_watchlist (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES wp_users(user_id) ON DELETE CASCADE,
                        property_id VARCHAR(255) NOT NULL,
                        property_data JSONB,
                        added_date TIMESTAMP DEFAULT NOW(),
                        address TEXT,
                        price DECIMAL(15,2),
                        status VARCHAR(50) DEFAULT 'active',
                        consumer_secret TEXT
                    );
                """,
                "analysis_reports": """
                    CREATE TABLE IF NOT EXISTS analysis_reports (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES wp_users(user_id) ON DELETE CASCADE,
                        report_data JSONB,
                        created_date TIMESTAMP DEFAULT NOW(),
                        report_type VARCHAR(100) DEFAULT 'investment_analysis',
                        property_address TEXT,
                        consumer_secret TEXT
                    );
                """,
                "auth_sessions": """
                    CREATE TABLE IF NOT EXISTS auth_sessions (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER REFERENCES wp_users(user_id) ON DELETE CASCADE,
                        session_token TEXT NOT NULL,
                        expires_at TIMESTAMP NOT NULL,
                        created_at TIMESTAMP DEFAULT NOW(),
                        last_activity TIMESTAMP DEFAULT NOW(),
                        ip_address INET,
                        user_agent TEXT,
                        consumer_secret TEXT
                    );
                """
            }
            
            created_count = 0
            for table in missing_tables:
                if table in table_sql:
                    try:
                        # Execute SQL using Supabase RPC or direct SQL execution
                        self.client.rpc('execute_sql', {'sql': table_sql[table]}).execute()
                        created_count += 1
                        st.success(f"✅ Created table: {table}")
                    except Exception as e:
                        st.error(f"❌ Failed to create table {table}: {str(e)}")
                        # Try alternative method using PostgREST
                        try:
                            import psycopg2
                            # This would require database URL with password
                            st.warning(f"⚠️ Table {table} creation failed. Please run the database setup script manually.")
                        except:
                            pass
            
            return created_count == len(missing_tables)
            
        except Exception as e:
            st.error(f"❌ Error creating tables: {str(e)}")
            return False
    
    def get_user_usage(self, user_id: str) -> int:
        """Get current month's API usage with better error handling"""
        if not self.is_connected():
            st.warning("⚠️ Cannot track usage - database not connected")
            return 0
        
        current_month = datetime.now().strftime("%Y-%m")
        
        try:
            result = self.client.table("user_usage").select("*").eq("user_id", user_id).eq("month", current_month).execute()
            
            if result.data:
                return result.data[0]["usage_count"]
            else:
                try:
                    self.client.table("user_usage").insert({
                        "user_id": user_id,
                        "month": current_month,
                        "usage_count": 0,
                        "usage_type": "search",
                        "last_used": datetime.now().isoformat()
                    }).execute()
                except Exception as insert_error:
                    st.warning(f"Could not initialize usage tracking: {str(insert_error)}")
                return 0
        except Exception as e:
            st.warning(f"Usage tracking unavailable: {str(e)}")
            return 0
    
    def increment_usage(self, user_id: str, usage_type: str = "search") -> bool:
        """Increment user's API usage count with improved error handling"""
        if not self.is_connected():
            return False
        
        current_month = datetime.now().strftime("%Y-%m")
        
        try:
            # Get current usage
            result = self.client.table("user_usage").select("*").eq("user_id", user_id).eq("month", current_month).execute()
            
            if result.data:
                # Update existing record
                new_count = result.data[0]["usage_count"] + 1
                self.client.table("user_usage").update({
                    "usage_count": new_count,
                    "last_used": datetime.now().isoformat()
                }).eq("user_id", user_id).eq("month", current_month).execute()
            else:
                # Create new record
                self.client.table("user_usage").insert({
                    "user_id": user_id,
                    "month": current_month,
                    "usage_count": 1,
                    "usage_type": usage_type,
                    "last_used": datetime.now().isoformat()
                }).execute()
            
            return True
        except Exception as e:
            st.warning(f"Could not update usage tracking: {str(e)}")
            return False
    
    def save_property_data(self, user_id: str, property_data: Dict[str, Any], search_type: str = "basic"):
        """Save comprehensive property data with better error handling"""
        if not self.is_connected():
            st.info("💾 Property data not saved - database not connected")
            return
            
        try:
            self.client.table("property_searches").insert({
                "user_id": user_id,
                "property_data": property_data,
                "search_date": datetime.now().isoformat(),
                "search_type": search_type,
                "address": property_data.get("formattedAddress", ""),
                "property_type": property_data.get("propertyType", ""),
                "price": property_data.get("lastSalePrice"),
                "bedrooms": property_data.get("bedrooms"),
                "bathrooms": property_data.get("bathrooms"),
                "square_footage": property_data.get("squareFootage")
            }).execute()
        except Exception as e:
            st.warning(f"Could not save property data: {str(e)}")
    
    def get_user_searches(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's recent property searches with error handling"""
        if not self.is_connected():
            return []
            
        try:
            result = self.client.table("property_searches").select("*").eq("user_id", user_id).order("search_date", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            st.warning(f"Could not fetch search history: {str(e)}")
            return []
    
    def save_to_watchlist(self, user_id: str, property_data: Dict[str, Any]) -> bool:
        """Add property to user's watchlist with error handling"""
        if not self.is_connected():
            st.info("💾 Cannot save to watchlist - database not connected")
            return False
            
        try:
            property_id = property_data.get("id") or hashlib.md5(
                property_data.get("formattedAddress", "").encode()
            ).hexdigest()
            
            self.client.table("property_watchlist").insert({
                "user_id": user_id,
                "property_id": property_id,
                "property_data": property_data,
                "added_date": datetime.now().isoformat(),
                "address": property_data.get("formattedAddress", ""),
                "price": property_data.get("lastSalePrice"),
                "status": "active"
            }).execute()
            return True
        except Exception as e:
            st.warning(f"Could not add to watchlist: {str(e)}")
            return False
    
    def get_watchlist(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's property watchlist with error handling"""
        if not self.is_connected():
            return []
            
        try:
            result = self.client.table("property_watchlist").select("*").eq("user_id", user_id).eq("status", "active").order("added_date", desc=True).execute()
            return result.data if result.data else []
        except Exception as e:
            st.warning(f"Could not fetch watchlist: {str(e)}")
            return []
    
    def save_analysis_report(self, user_id: str, report_data: Dict[str, Any]) -> bool:
        """Save property analysis report with error handling"""
        if not self.is_connected():
            st.info("💾 Cannot save analysis report - database not connected")
            return False
            
        try:
            self.client.table("analysis_reports").insert({
                "user_id": user_id,
                "report_data": report_data,
                "created_date": datetime.now().isoformat(),
                "report_type": report_data.get("type", "property_analysis"),
                "property_address": report_data.get("address", "")
            }).execute()
            return True
        except Exception as e:
            st.warning(f"Could not save analysis report: {str(e)}")
            return False

class PropertyAnalyzer:
    """Advanced property analysis and investment calculations"""
    
    @staticmethod
    def calculate_investment_metrics(property_data: Dict[str, Any], rental_estimate: float, 
                                   down_payment_percent: float = 20, interest_rate: float = 6.5,
                                   loan_term_years: int = 30) -> Dict[str, Any]:
        """Calculate comprehensive investment metrics"""
        
        purchase_price = property_data.get("lastSalePrice") or property_data.get("price", 0)
        if not purchase_price:
            return {"error": "No purchase price available"}
        
        # Basic calculations
        down_payment = purchase_price * (down_payment_percent / 100)
        loan_amount = purchase_price - down_payment
        
        # Monthly mortgage payment calculation
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term_years * 12
        
        if monthly_rate > 0:
            monthly_payment = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        else:
            monthly_payment = loan_amount / num_payments
        
        # Operating expenses (estimated)
        monthly_rental = rental_estimate
        property_tax_monthly = (purchase_price * 0.012) / 12  # 1.2% annual
        insurance_monthly = (purchase_price * 0.003) / 12    # 0.3% annual
        maintenance_monthly = monthly_rental * 0.05          # 5% of rent
        vacancy_allowance = monthly_rental * 0.08            # 8% vacancy
        property_mgmt = monthly_rental * 0.10                # 10% property management
        
        total_monthly_expenses = (monthly_payment + property_tax_monthly + 
                                insurance_monthly + maintenance_monthly + 
                                vacancy_allowance + property_mgmt)
        
        # Cash flow calculations
        monthly_cash_flow = monthly_rental - total_monthly_expenses
        annual_cash_flow = monthly_cash_flow * 12
        
        # Return calculations
        cash_on_cash_return = (annual_cash_flow / down_payment) * 100 if down_payment > 0 else 0
        cap_rate = ((monthly_rental * 12) / purchase_price) * 100
        
        # 1% rule check
        one_percent_rule = (monthly_rental / purchase_price) * 100
        
        return {
            "purchase_price": purchase_price,
            "down_payment": down_payment,
            "loan_amount": loan_amount,
            "monthly_payment": monthly_payment,
            "monthly_rental": monthly_rental,
            "monthly_cash_flow": monthly_cash_flow,
            "annual_cash_flow": annual_cash_flow,
            "cash_on_cash_return": cash_on_cash_return,
            "cap_rate": cap_rate,
            "one_percent_rule": one_percent_rule,
            "total_monthly_expenses": total_monthly_expenses,
            "property_tax_monthly": property_tax_monthly,
            "insurance_monthly": insurance_monthly,
            "maintenance_monthly": maintenance_monthly,
            "vacancy_allowance": vacancy_allowance,
            "property_mgmt": property_mgmt
        }
    
    @staticmethod
    def analyze_neighborhood_trends(comparable_properties: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze neighborhood market trends"""
        if not comparable_properties:
            return {"error": "No comparable properties available"}
        
        # Extract price data
        prices = []
        years = []
        property_types = []
        
        for prop in comparable_properties:
            if prop.get("lastSalePrice") and prop.get("lastSaleDate"):
                prices.append(prop["lastSalePrice"])
                try:
                    year = datetime.fromisoformat(prop["lastSaleDate"].replace("Z", "+00:00")).year
                    years.append(year)
                except:
                    years.append(datetime.now().year)
                property_types.append(prop.get("propertyType", "Unknown"))
        
        if not prices:
            return {"error": "No price data available"}
        
        # Statistical analysis
        avg_price = np.mean(prices)
        median_price = np.median(prices)
        price_std = np.std(prices)
        min_price = min(prices)
        max_price = max(prices)
        
        # Price per square foot analysis
        price_per_sqft = []
        for prop in comparable_properties:
            if prop.get("lastSalePrice") and prop.get("squareFootage"):
                if prop["squareFootage"] > 0:
                    price_per_sqft.append(prop["lastSalePrice"] / prop["squareFootage"])
        
        avg_price_per_sqft = np.mean(price_per_sqft) if price_per_sqft else 0
        
        # Property type distribution
        type_counts = pd.Series(property_types).value_counts().to_dict()
        
        return {
            "total_properties": len(comparable_properties),
            "avg_price": avg_price,
            "median_price": median_price,
            "price_std": price_std,
            "min_price": min_price,
            "max_price": max_price,
            "avg_price_per_sqft": avg_price_per_sqft,
            "property_type_distribution": type_counts,
            "price_range": max_price - min_price,
            "coefficient_of_variation": (price_std / avg_price) * 100 if avg_price > 0 else 0
        }
    
    @staticmethod
    def calculate_appreciation_forecast(historical_data: List[Dict[str, Any]], years_ahead: int = 5) -> Dict[str, Any]:
        """Calculate property appreciation forecast"""
        if len(historical_data) < 2:
            return {"error": "Insufficient historical data"}
        
        # Extract price and date data
        price_data = []
        for data in historical_data:
            if data.get("price") and data.get("date"):
                try:
                    date_obj = datetime.fromisoformat(data["date"].replace("Z", "+00:00"))
                    price_data.append((date_obj, data["price"]))
                except:
                    continue
        
        if len(price_data) < 2:
            return {"error": "Insufficient valid price data"}
        
        # Sort by date
        price_data.sort(key=lambda x: x[0])
        
        # Calculate annual appreciation rate
        start_date, start_price = price_data[0]
        end_date, end_price = price_data[-1]
        
        years_elapsed = (end_date - start_date).days / 365.25
        if years_elapsed <= 0:
            return {"error": "Invalid date range"}
        
        annual_appreciation = ((end_price / start_price) ** (1 / years_elapsed) - 1) * 100
        
        # Forecast future values
        current_value = end_price
        forecasts = []
        
        for year in range(1, years_ahead + 1):
            future_value = current_value * ((1 + annual_appreciation / 100) ** year)
            forecasts.append({
                "year": year,
                "projected_value": future_value,
                "projected_gain": future_value - current_value
            })
        
        return {
            "annual_appreciation_rate": annual_appreciation,
            "current_value": current_value,
            "forecasts": forecasts,
            "total_projected_gain": forecasts[-1]["projected_gain"] if forecasts else 0
        }

def render_wordpress_auth(wp_auth: WordPressAuthManager):
    """Render WordPress authentication interface"""
    st.markdown('<h1 class="main-header">🔐 WordPress Authentication</h1>', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["🔑 Sign In", "🔄 Reset Password"])
    
    with tab1:
        st.markdown('<div class="sub-header">Sign In to Your Account</div>', unsafe_allow_html=True)
        
        with st.form("wp_signin_form"):
            col1, col2 = st.columns([2, 1])
            
            with col1:
                username = st.text_input("WordPress Username", key="wp_username")
                password = st.text_input("WordPress Password", type="password", key="wp_password")
                consumer_secret = st.text_input("Consumer Secret (Optional)", type="password", key="wp_consumer_secret", 
                                               help="Required for subscription retrieval API access")
            
            with col2:
                st.info("""
                **Access Requirements:**
                - Active subscription on AiPropIQ
                - Valid WordPress credentials
                - Consumer Secret for API access
                """)
            
            submit_signin = st.form_submit_button("🚀 Sign In", type="primary")
            
            if submit_signin:
                if not username or not password:
                    st.error("Please fill in username and password.")
                else:
                    with st.spinner("Authenticating with WordPress..."):
                        valid, result = wp_auth.check_subscription(username, password, consumer_secret)
                        
                        if valid:
                            st.session_state.authenticated = True
                            st.session_state.user_data = result
                            st.session_state.username = username
                            st.session_state.password = password
                            st.session_state.consumer_secret = consumer_secret
                            
                            # Set usage limits based on role
                            if result.get("role") == "admin":
                                st.session_state.max_usage = 1000  # Admin gets higher limit
                            else:
                                st.session_state.max_usage = 100   # Subscribers get standard limit
                            
                            st.success(f"✅ Welcome {username}! Role: {result.get('role', 'subscriber')}")
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error(f"❌ Login failed: {result.get('error', 'Unknown error')}")
    
    with tab2:
        st.markdown('<div class="sub-header">Reset Password</div>', unsafe_allow_html=True)
        
        st.info("""
        **Password Reset Process:**
        1. Contact your WordPress administrator
        2. Or use the WordPress login page directly
        3. Password reset functionality depends on your WordPress setup
        """)
        
        st.markdown("""
        **Alternative Access Methods:**
        - Use your consumer secret for API access
        - Contact support for assistance
        """)

def render_enhanced_dashboard(user_data: Dict[str, Any], supabase_manager: SupabaseManager):
    """Render comprehensive user dashboard"""
    username = user_data.get("user_name", "User")
    role = user_data.get("role", "subscriber")
    
    # Sidebar user info
    st.sidebar.markdown(f"""
    <div class="metric-card">
        <h3>👋 Welcome, {username}</h3>
        <p><strong>Role:</strong> {role.title()}</p>
        <p><strong>Status:</strong> {user_data.get('status', 'active').title()}</p>
        <p><strong>Product:</strong> {user_data.get('product_name', 'N/A')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Control buttons
    col1, col2, col3 = st.sidebar.columns(3)
    with col1:
        if st.button("🚪 Sign Out"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()
    
    with col2:
        show_dashboard = st.button("📊 Dashboard")
    
    with col3:
        show_analytics = st.button("📈 Analytics")
    
    # Usage statistics
    user_id = hashlib.md5(username.encode()).hexdigest()
    current_usage = supabase_manager.get_user_usage(user_id)
    max_usage = st.session_state.get("max_usage", 25)
    remaining_searches = max_usage - current_usage
    
    st.sidebar.markdown(f"""
    <div class="metric-card">
        <h4>📊 Usage Statistics</h4>
        <p><strong>Used:</strong> {current_usage}/{max_usage}</p>
        <p><strong>Remaining:</strong> {remaining_searches}</p>
        <div style="background: rgba(255,255,255,0.3); border-radius: 10px; height: 10px; margin: 10px 0;">
            <div style="background: white; height: 100%; width: {(current_usage/max_usage)*100}%; border-radius: 10px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    if show_dashboard or st.session_state.get("show_dashboard", False):
        st.session_state.show_dashboard = True
        render_user_dashboard(user_id, supabase_manager)
        return True
    
    if show_analytics or st.session_state.get("show_analytics", False):
        st.session_state.show_analytics = True
        render_analytics_dashboard(user_id, supabase_manager)
        return True
    
    return False

def render_user_dashboard(user_id: str, supabase_manager: SupabaseManager):
    """Render detailed user dashboard"""
    st.markdown('<h1 class="main-header">📊 User Dashboard</h1>', unsafe_allow_html=True)
    
    # Recent searches
    st.markdown('<div class="sub-header">🕐 Recent Property Searches</div>', unsafe_allow_html=True)
    recent_searches = supabase_manager.get_user_searches(user_id, limit=10)
    
    if recent_searches:
        for i, search in enumerate(recent_searches):
            property_data = search["property_data"]
            search_date = datetime.fromisoformat(search["search_date"].replace("Z", "+00:00"))
            
            with st.expander(f"🏠 {property_data.get('formattedAddress', 'Unknown Address')} - {search_date.strftime('%Y-%m-%d %H:%M')}"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Property Type", property_data.get('propertyType', 'N/A'))
                    st.metric("Bedrooms", property_data.get('bedrooms', 'N/A'))
                
                with col2:
                    st.metric("Bathrooms", property_data.get('bathrooms', 'N/A'))
                    st.metric("Square Feet", format_number(property_data.get('squareFootage')))
                
                with col3:
                    st.metric("Year Built", property_data.get('yearBuilt', 'N/A'))
                    st.metric("Last Sale", format_currency(property_data.get('lastSalePrice')))
                
                with col4:
                    if st.button(f"📌 Add to Watchlist", key=f"watchlist_{i}"):
                        if supabase_manager.save_to_watchlist(user_id, property_data):
                            st.success("Added to watchlist!")
                    
                    if st.button(f"🔍 Re-analyze", key=f"reanalyze_{i}"):
                        st.session_state.selected_property = property_data
                        st.session_state.show_analysis = True
                        st.rerun()
    else:
        st.info("No recent searches found. Start by searching for a property!")
    
    # Watchlist
    st.markdown('<div class="sub-header">📌 Property Watchlist</div>', unsafe_allow_html=True)
    watchlist = supabase_manager.get_watchlist(user_id)
    
    if watchlist:
        for item in watchlist:
            property_data = item["property_data"]
            added_date = datetime.fromisoformat(item["added_date"].replace("Z", "+00:00"))
            
            with st.expander(f"⭐ {property_data.get('formattedAddress', 'Unknown Address')} - Added {added_date.strftime('%Y-%m-%d')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.write(f"**Type:** {property_data.get('propertyType', 'N/A')}")
                    st.write(f"**Bedrooms:** {property_data.get('bedrooms', 'N/A')}")
                    st.write(f"**Bathrooms:** {property_data.get('bathrooms', 'N/A')}")
                
                with col2:
                    st.write(f"**Square Feet:** {format_number(property_data.get('squareFootage'))}")
                    st.write(f"**Year Built:** {property_data.get('yearBuilt', 'N/A')}")
                    st.write(f"**Last Sale:** {format_currency(property_data.get('lastSalePrice'))}")
                
                with col3:
                    if st.button("🔍 Analyze", key=f"analyze_watchlist_{item['property_id']}"):
                        st.session_state.selected_property = property_data
                        st.session_state.show_analysis = True
                        st.rerun()
    else:
        st.info("Your watchlist is empty. Add properties from your searches!")

def render_analytics_dashboard(user_id: str, supabase_manager: SupabaseManager):
    """Render analytics dashboard"""
    st.markdown('<h1 class="main-header">📈 Analytics Dashboard</h1>', unsafe_allow_html=True)
    
    # Get user's search data
    searches = supabase_manager.get_user_searches(user_id, limit=50)
    
    if not searches:
        st.info("No data available for analytics. Start searching for properties!")
        return
    
    # Prepare data for analysis
    search_dates = []
    property_types = []
    prices = []
    bedrooms = []
    bathrooms = []
    square_footage = []
    
    for search in searches:
        data = search["property_data"]
        search_dates.append(datetime.fromisoformat(search["search_date"].replace("Z", "+00:00")))
        property_types.append(data.get("propertyType", "Unknown"))
        if data.get("lastSalePrice"):
            prices.append(data["lastSalePrice"])
        if data.get("bedrooms"):
            bedrooms.append(data["bedrooms"])
        if data.get("bathrooms"):
            bathrooms.append(data["bathrooms"])
        if data.get("squareFootage"):
            square_footage.append(data["squareFootage"])
    
    # Search activity over time
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown('<div class="sub-header">🔍 Search Activity</div>', unsafe_allow_html=True)
        
        # Group searches by date
        search_df = pd.DataFrame({"date": search_dates})
        search_df["date"] = search_df["date"].dt.date
        daily_searches = search_df.groupby("date").size().reset_index(name="searches")
        
        fig = px.line(daily_searches, x="date", y="searches", title="Daily Search Activity")
        fig.update_traces(line=dict(width=3), marker=dict(size=6))
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.markdown('<div class="sub-header">🏠 Property Types</div>', unsafe_allow_html=True)
        
        type_counts = pd.Series(property_types).value_counts()
        fig = px.pie(values=type_counts.values, names=type_counts.index, title="Property Type Distribution")
        st.plotly_chart(fig, use_container_width=True)
    
    # Price analysis
    if prices:
        st.markdown('<div class="sub-header">💰 Price Analysis</div>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Average Price", format_currency(np.mean(prices)))
        with col2:
            st.metric("Median Price", format_currency(np.median(prices)))
        with col3:
            st.metric("Min Price", format_currency(min(prices)))
        with col4:
            st.metric("Max Price", format_currency(max(prices)))
        
        # Price distribution
        fig = px.histogram(x=prices, nbins=20, title="Price Distribution")
        fig.update_layout(xaxis_title="Price ($)", yaxis_title="Count")
        st.plotly_chart(fig, use_container_width=True)
    
    # Property characteristics
    if bedrooms and bathrooms:
        st.markdown('<div class="sub-header">🛏️ Property Characteristics</div>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            bedroom_counts = pd.Series(bedrooms).value_counts().sort_index()
            fig = px.bar(x=bedroom_counts.index, y=bedroom_counts.values, title="Bedroom Distribution")
            fig.update_layout(xaxis_title="Bedrooms", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            bathroom_counts = pd.Series(bathrooms).value_counts().sort_index()
            fig = px.bar(x=bathroom_counts.index, y=bathroom_counts.values, title="Bathroom Distribution")
            fig.update_layout(xaxis_title="Bathrooms", yaxis_title="Count")
            st.plotly_chart(fig, use_container_width=True)

def render_property_search_interface(rentcast_api: RentCastAPI, supabase_manager: SupabaseManager, user_id: str):
    """Render enhanced property search interface"""
    st.markdown('<h1 class="main-header">🏠 Enhanced Property Search & Analysis</h1>', unsafe_allow_html=True)
    
    # Search options
    search_type = st.selectbox(
        "Search Type",
        ["Basic Property Search", "Rental Analysis", "Investment Analysis", "Market Comparison", "Neighborhood Analysis"],
        help="Choose the type of analysis you want to perform"
    )
    
    # Address input with suggestions
    col1, col2 = st.columns([3, 1])
    
    with col1:
        address = st.text_input(
            "🏠 Property Address",
            placeholder="e.g., 123 Main St, New York, NY 10001",
            help="Enter the full address including city, state, and zip code for best results"
        )
    
    with col2:
        st.markdown("<br>", unsafe_allow_html=True)  # Spacing
        search_button = st.button("🔍 Search & Analyze", type="primary")
    
    # Advanced search options
    with st.expander("🔧 Advanced Search Options"):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            include_comparables = st.checkbox("Include Comparable Properties", value=True)
            include_rental_estimates = st.checkbox("Include Rental Estimates", value=True)
        
        with col2:
            comparable_radius = st.slider("Comparable Properties Radius (miles)", 0.1, 2.0, 0.5, 0.1)
            max_comparables = st.slider("Max Comparable Properties", 5, 50, 20, 5)
        
        with col3:
            save_to_watchlist = st.checkbox("Auto-save to Watchlist", value=False)
            generate_report = st.checkbox("Generate PDF Report", value=False)
    
    if search_button and address:
        # Check usage limits
        current_usage = supabase_manager.get_user_usage(user_id)
        max_usage = st.session_state.get("max_usage", 25)
        
        if current_usage >= max_usage:
            st.error(f"Monthly search limit reached! ({current_usage}/{max_usage})")
            return
        
        # Increment usage
        if not supabase_manager.increment_usage(user_id, search_type.lower().replace(" ", "_")):
            st.error("Failed to update usage count. Please try again.")
            return
        
        with st.spinner(f"Performing {search_type.lower()}..."):
            # Basic property search
            property_result = rentcast_api.search_properties(address)
            
            if not property_result:
                st.error("No property data found or API error occurred.")
                return
            
            # Handle different API response formats
            if isinstance(property_result, list) and len(property_result) > 0:
                property_data = property_result[0]
            elif isinstance(property_result, dict) and property_result.get("properties"):
                properties = property_result.get("properties", [])
                if not properties:
                    st.warning("No properties found for the given address.")
                    return
                property_data = properties[0]
            else:
                st.warning("No properties found for the given address.")
                return
            
            # Save search data
            supabase_manager.save_property_data(user_id, property_data, search_type)
            
            # Auto-save to watchlist if requested
            if save_to_watchlist:
                supabase_manager.save_to_watchlist(user_id, property_data)
                st.success("Property added to watchlist!")
            
            st.success(f"Analysis complete! Searches remaining: {max_usage - current_usage - 1}")
            
            # Display comprehensive property analysis
            display_comprehensive_property_analysis(
                property_data, rentcast_api, search_type, 
                include_comparables, include_rental_estimates,
                comparable_radius, max_comparables
            )
            
            # Generate report if requested
            if generate_report:
                generate_property_report(property_data, search_type)

def display_comprehensive_property_analysis(property_data: Dict[str, Any], rentcast_api: RentCastAPI, 
                                          search_type: str, include_comparables: bool, 
                                          include_rental_estimates: bool, comparable_radius: float, 
                                          max_comparables: int):
    """Display comprehensive property analysis"""
    
    # Property header
    st.markdown(f"""
    <div class="property-summary">
        <h2>📍 {property_data.get('formattedAddress', 'Property Analysis')}</h2>
        <p><strong>Analysis Type:</strong> {search_type}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Basic property overview
    display_enhanced_property_overview(property_data)
    
    # Rental estimates
    rental_estimate = 0
    if include_rental_estimates:
        with st.spinner("Getting rental estimates..."):
            rental_data = rentcast_api.get_rental_estimates(property_data.get('formattedAddress', ''))
            if rental_data:
                rental_estimate = display_rental_analysis(rental_data)
    
    # Investment analysis
    if search_type == "Investment Analysis" or rental_estimate > 0:
        display_investment_analysis(property_data, rental_estimate)
    
    # Comparable properties
    comparable_properties = []
    if include_comparables:
        with st.spinner("Finding comparable properties..."):
            comp_data = rentcast_api.get_comparable_properties(
                property_data.get('formattedAddress', ''), 
                comparable_radius
            )
            if comp_data and isinstance(comp_data, list):
                comparable_properties = comp_data[:max_comparables]
                display_comparable_analysis(comparable_properties, property_data)
    
    # Market analysis
    if search_type in ["Market Comparison", "Neighborhood Analysis"]:
        display_market_analysis(property_data, comparable_properties)
    
    # Advanced analytics
    display_advanced_analytics(property_data, comparable_properties)
    
    # Export options
    display_export_options(property_data, search_type)

def display_enhanced_property_overview(property_data: Dict[str, Any]):
    """Display enhanced property overview with visualizations"""
    st.markdown('<div class="sub-header">🏠 Property Overview</div>', unsafe_allow_html=True)
    
    # Main metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric("Property Type", property_data.get("propertyType", "N/A"))
        st.metric("Year Built", property_data.get("yearBuilt", "N/A"))
    
    with col2:
        st.metric("Bedrooms", property_data.get("bedrooms", "N/A"))
        st.metric("Bathrooms", property_data.get("bathrooms", "N/A"))
    
    with col3:
        st.metric("Square Footage", format_number(property_data.get("squareFootage")))
        st.metric("Lot Size", format_number(property_data.get("lotSize")))
    
    with col4:
        st.metric("Last Sale Price", format_currency(property_data.get("lastSalePrice")))
        last_sale_date = property_data.get("lastSaleDate")
        if last_sale_date:
            try:
                date_obj = datetime.fromisoformat(last_sale_date.replace("Z", "+00:00"))
                formatted_date = date_obj.strftime("%Y-%m-%d")
            except:
                formatted_date = last_sale_date[:10] if len(last_sale_date) >= 10 else last_sale_date
        else:
            formatted_date = "N/A"
        st.metric("Last Sale Date", formatted_date)
    
    with col5:
        # Calculate price per square foot
        price_per_sqft = 0
        if property_data.get("lastSalePrice") and property_data.get("squareFootage"):
            if property_data["squareFootage"] > 0:
                price_per_sqft = property_data["lastSalePrice"] / property_data["squareFootage"]
        
        st.metric("Price per Sq Ft", f"${price_per_sqft:.2f}" if price_per_sqft > 0 else "N/A")
        
        # Property age
        current_year = datetime.now().year
        year_built = property_data.get("yearBuilt")
        if year_built:
            property_age = current_year - int(year_built)
            st.metric("Property Age", f"{property_age} years")
        else:
            st.metric("Property Age", "N/A")
    
    # Additional details
    st.markdown("---")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("County", property_data.get("county", "N/A"))
        st.metric("Zoning", property_data.get("zoning", "N/A"))
    
    with col2:
        hoa_fee = property_data.get("hoa", {}).get("fee")
        st.metric("HOA Fee (Monthly)", format_currency(hoa_fee) if hoa_fee else "None")
        st.metric("Owner Occupied", "Yes" if property_data.get("ownerOccupied") else "No")
    
    with col3:
        st.metric("Assessor ID", property_data.get("assessorID", "N/A"))
        st.metric("Subdivision", property_data.get("subdivision", "N/A"))
    
    with col4:
        # Tax information
        tax_assessments = property_data.get("taxAssessments", {})
        property_taxes = property_data.get("propertyTaxes", {})
        
        # Get latest assessment
        if tax_assessments:
            latest_year = max(tax_assessments.keys())
            latest_assessment = tax_assessments[latest_year].get("total", 0)
            st.metric("Latest Assessment", format_currency(latest_assessment))
        else:
            st.metric("Latest Assessment", "N/A")
        
        # Get latest property tax
        if property_taxes:
            latest_year = max(property_taxes.keys())
            latest_tax = property_taxes[latest_year].get("total", 0)
            st.metric("Annual Property Tax", format_currency(latest_tax))
        else:
            st.metric("Annual Property Tax", "N/A")

def display_rental_analysis(rental_data: Dict[str, Any]) -> float:
    """Display rental analysis and return estimated rent"""
    st.markdown('<div class="sub-header">💰 Rental Analysis</div>', unsafe_allow_html=True)
    
    if not rental_data:
        st.warning("No rental data available")
        return 0
    
    # Extract rental estimates
    rent_estimate = rental_data.get("rent", 0)
    rent_range_low = rental_data.get("rentRangeLow", 0)
    rent_range_high = rental_data.get("rentRangeHigh", 0)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Estimated Monthly Rent", format_currency(rent_estimate))
    
    with col2:
        st.metric("Rent Range Low", format_currency(rent_range_low))
    
    with col3:
        st.metric("Rent Range High", format_currency(rent_range_high))
    
    with col4:
        if rent_range_high > rent_range_low > 0:
            rent_spread = rent_range_high - rent_range_low
            st.metric("Rent Range Spread", format_currency(rent_spread))
        else:
            st.metric("Rent Range Spread", "N/A")
    
    # Rental yield calculation if property price is available
    if rent_estimate > 0:
        st.markdown("### 📊 Rental Yield Analysis")
        
        # Create rental yield visualization
        monthly_rent = rent_estimate
        annual_rent = monthly_rent * 12
        
        # Display rental metrics
        col1, col2 = st.columns(2)
        
        with col1:
            st.metric("Annual Rental Income", format_currency(annual_rent))
            st.metric("Monthly Cash Flow (Gross)", format_currency(monthly_rent))
        
        with col2:
            # Estimated expenses (rough calculation)
            estimated_expenses = monthly_rent * 0.3  # 30% of rent for expenses
            net_monthly = monthly_rent - estimated_expenses
            st.metric("Estimated Monthly Expenses", format_currency(estimated_expenses))
            st.metric("Estimated Net Monthly", format_currency(net_monthly))
    
    return rent_estimate

def display_investment_analysis(property_data: Dict[str, Any], rental_estimate: float):
    """Display comprehensive investment analysis"""
    st.markdown('<div class="sub-header">📈 Investment Analysis</div>', unsafe_allow_html=True)
    
    if rental_estimate <= 0:
        st.warning("Rental estimate required for investment analysis")
        return
    
    # Investment parameters
    col1, col2, col3 = st.columns(3)
    
    with col1:
        down_payment_percent = st.slider("Down Payment %", 10, 50, 20, 5)
        interest_rate = st.slider("Interest Rate %", 3.0, 10.0, 6.5, 0.25)
    
    with col2:
        loan_term = st.slider("Loan Term (years)", 15, 30, 30, 5)
        property_tax_rate = st.slider("Property Tax Rate %", 0.5, 3.0, 1.2, 0.1)
    
    with col3:
        insurance_rate = st.slider("Insurance Rate %", 0.1, 1.0, 0.3, 0.1)
        maintenance_rate = st.slider("Maintenance % of Rent", 3, 15, 5, 1)
    
    # Calculate investment metrics
    metrics = PropertyAnalyzer.calculate_investment_metrics(
        property_data, rental_estimate, down_payment_percent, 
        interest_rate, loan_term
    )
    
    if "error" in metrics:
        st.error(metrics["error"])
        return
    
    # Display investment metrics
    st.markdown("### 💰 Investment Metrics")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="investment-card">
            <h4>💵 Purchase Details</h4>
            <p><strong>Purchase Price:</strong> {format_currency(metrics['purchase_price'])}</p>
            <p><strong>Down Payment:</strong> {format_currency(metrics['down_payment'])}</p>
            <p><strong>Loan Amount:</strong> {format_currency(metrics['loan_amount'])}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="investment-card">
            <h4>🏦 Monthly Payments</h4>
            <p><strong>Mortgage Payment:</strong> {format_currency(metrics['monthly_payment'])}</p>
            <p><strong>Total Expenses:</strong> {format_currency(metrics['total_monthly_expenses'])}</p>
            <p><strong>Net Cash Flow:</strong> {format_currency(metrics['monthly_cash_flow'])}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="investment-card">
            <h4>📊 Return Metrics</h4>
            <p><strong>Cash-on-Cash Return:</strong> {metrics['cash_on_cash_return']:.2f}%</p>
            <p><strong>Cap Rate:</strong> {metrics['cap_rate']:.2f}%</p>
            <p><strong>1% Rule:</strong> {metrics['one_percent_rule']:.2f}%</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        # Investment quality indicators
        cash_flow_color = "green" if metrics['monthly_cash_flow'] > 0 else "red"
        one_percent_color = "green" if metrics['one_percent_rule'] >= 1.0 else "orange"
        cap_rate_color = "green" if metrics['cap_rate'] >= 8.0 else "orange"
        
        st.markdown(f"""
        <div class="investment-card">
            <h4>🎯 Investment Quality</h4>
            <p style="color: {cash_flow_color}"><strong>Cash Flow:</strong> {'Positive' if metrics['monthly_cash_flow'] > 0 else 'Negative'}</p>
            <p style="color: {one_percent_color}"><strong>1% Rule:</strong> {'Pass' if metrics['one_percent_rule'] >= 1.0 else 'Fail'}</p>
            <p style="color: {cap_rate_color}"><strong>Cap Rate:</strong> {'Good' if metrics['cap_rate'] >= 8.0 else 'Fair'}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Expense breakdown chart
    st.markdown("### 📊 Monthly Expense Breakdown")
    
    expense_data = {
        "Mortgage Payment": metrics['monthly_payment'],
        "Property Tax": metrics['property_tax_monthly'],
        "Insurance": metrics['insurance_monthly'],
        "Maintenance": metrics['maintenance_monthly'],
        "Vacancy Allowance": metrics['vacancy_allowance'],
        "Property Management": metrics['property_mgmt']
    }
    
    fig = px.pie(
        values=list(expense_data.values()),
        names=list(expense_data.keys()),
        title="Monthly Expense Breakdown"
    )
    st.plotly_chart(fig, use_container_width=True)
    
    # Cash flow projection
    st.markdown("### 📈 10-Year Cash Flow Projection")
    
    years = list(range(1, 11))
    annual_cash_flows = [metrics['annual_cash_flow'] * year for year in years]
    cumulative_cash_flows = [sum(annual_cash_flows[:i+1]) for i in range(len(annual_cash_flows))]
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=years, y=annual_cash_flows, mode='lines+markers', name='Annual Cash Flow'))
    fig.add_trace(go.Scatter(x=years, y=cumulative_cash_flows, mode='lines+markers', name='Cumulative Cash Flow'))
    
    fig.update_layout(
        title="Cash Flow Projection",
        xaxis_title="Year",
        yaxis_title="Cash Flow ($)",
        yaxis=dict(tickformat="$,.0f")
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_comparable_analysis(comparable_properties: List[Dict[str, Any]], target_property: Dict[str, Any]):
    """Display comparable properties analysis"""
    st.markdown('<div class="sub-header">🏘️ Comparable Properties Analysis</div>', unsafe_allow_html=True)
    
    if not comparable_properties:
        st.warning("No comparable properties found")
        return
    
    # Analyze neighborhood trends
    neighborhood_analysis = PropertyAnalyzer.analyze_neighborhood_trends(comparable_properties)
    
    if "error" in neighborhood_analysis:
        st.error(neighborhood_analysis["error"])
        return
    
    # Display neighborhood statistics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Properties Found", neighborhood_analysis["total_properties"])
        st.metric("Average Price", format_currency(neighborhood_analysis["avg_price"]))
    
    with col2:
        st.metric("Median Price", format_currency(neighborhood_analysis["median_price"]))
        st.metric("Price Range", format_currency(neighborhood_analysis["price_range"]))
    
    with col3:
        st.metric("Min Price", format_currency(neighborhood_analysis["min_price"]))
        st.metric("Max Price", format_currency(neighborhood_analysis["max_price"]))
    
    with col4:
        st.metric("Avg Price/Sq Ft", f"${neighborhood_analysis['avg_price_per_sqft']:.2f}")
        st.metric("Price Volatility", f"{neighborhood_analysis['coefficient_of_variation']:.1f}%")
    
    # Property type distribution
    st.markdown("### 🏠 Property Type Distribution")
    type_dist = neighborhood_analysis["property_type_distribution"]
    
    fig = px.bar(
        x=list(type_dist.keys()),
        y=list(type_dist.values()),
        title="Property Types in Neighborhood"
    )
    fig.update_layout(xaxis_title="Property Type", yaxis_title="Count")
    st.plotly_chart(fig, use_container_width=True)
    
    # Price distribution
    st.markdown("### 💰 Price Distribution Analysis")
    
    prices = [prop.get("lastSalePrice", 0) for prop in comparable_properties if prop.get("lastSalePrice")]
    
    if prices:
        fig = px.histogram(x=prices, nbins=15, title="Price Distribution in Neighborhood")
        fig.update_layout(xaxis_title="Sale Price ($)", yaxis_title="Count")
        
        # Add target property price line if available
        target_price = target_property.get("lastSalePrice")
        if target_price:
            fig.add_vline(x=target_price, line_dash="dash", line_color="red", 
                         annotation_text="Target Property")
        
        st.plotly_chart(fig, use_container_width=True)
    
    # Detailed comparable properties table
    st.markdown("### 📋 Detailed Comparable Properties")
    
    comp_data = []
    for prop in comparable_properties[:10]:  # Show top 10
        comp_data.append({
            "Address": prop.get("formattedAddress", "N/A"),
            "Type": prop.get("propertyType", "N/A"),
            "Bedrooms": prop.get("bedrooms", "N/A"),
            "Bathrooms": prop.get("bathrooms", "N/A"),
            "Sq Ft": prop.get("squareFootage", "N/A"),
            "Year Built": prop.get("yearBuilt", "N/A"),
            "Sale Price": format_currency(prop.get("lastSalePrice")),
            "Price/Sq Ft": f"${prop.get('lastSalePrice', 0) / prop.get('squareFootage', 1):.2f}" if prop.get("lastSalePrice") and prop.get("squareFootage") else "N/A"
        })
    
    if comp_data:
        df = pd.DataFrame(comp_data)
        st.dataframe(df, use_container_width=True)

def display_market_analysis(property_data: Dict[str, Any], comparable_properties: List[Dict[str, Any]]):
    """Display comprehensive market analysis"""
    st.markdown('<div class="sub-header">📊 Market Analysis</div>', unsafe_allow_html=True)
    
    # Extract city and state for market data
    address = property_data.get("formattedAddress", "")
    city = property_data.get("city", "")
    state = property_data.get("state", "")
    
    if not city or not state:
        st.warning("City and state information required for market analysis")
        return
    
    st.markdown(f"### 🏙️ Market Analysis for {city}, {state}")
    
    # Market trends from comparable properties
    if comparable_properties:
        # Price trends over time
        price_data = []
        for prop in comparable_properties:
            if prop.get("lastSalePrice") and prop.get("lastSaleDate"):
                try:
                    sale_date = datetime.fromisoformat(prop["lastSaleDate"].replace("Z", "+00:00"))
                    price_data.append({
                        "date": sale_date,
                        "price": prop["lastSalePrice"],
                        "price_per_sqft": prop["lastSalePrice"] / prop["squareFootage"] if prop.get("squareFootage") else 0
                    })
                except:
                    continue
        
        if price_data:
            # Sort by date
            price_data.sort(key=lambda x: x["date"])
            
            # Create price trend chart
            dates = [item["date"] for item in price_data]
            prices = [item["price"] for item in price_data]
            prices_per_sqft = [item["price_per_sqft"] for item in price_data if item["price_per_sqft"] > 0]
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.scatter(x=dates, y=prices, title="Sale Prices Over Time", trendline="ols")
                fig.update_layout(xaxis_title="Sale Date", yaxis_title="Sale Price ($)")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                if prices_per_sqft:
                    fig = px.scatter(x=dates[:len(prices_per_sqft)], y=prices_per_sqft, 
                                   title="Price per Sq Ft Over Time", trendline="ols")
                    fig.update_layout(xaxis_title="Sale Date", yaxis_title="Price per Sq Ft ($)")
                    st.plotly_chart(fig, use_container_width=True)
    
    # Market indicators
    st.markdown("### 📈 Market Indicators")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.markdown("""
        <div class="feature-card">
            <h4>🏠 Supply Indicators</h4>
            <p><strong>Properties Analyzed:</strong> {}</p>
            <p><strong>Property Types:</strong> {}</p>
            <p><strong>Age Range:</strong> {} years</p>
        </div>
        """.format(
            len(comparable_properties),
            len(set(prop.get("propertyType", "Unknown") for prop in comparable_properties)),
            f"{min(prop.get('yearBuilt', 2024) for prop in comparable_properties if prop.get('yearBuilt'))} - {max(prop.get('yearBuilt', 2024) for prop in comparable_properties if prop.get('yearBuilt'))}" if comparable_properties else "N/A"
        ), unsafe_allow_html=True)
    
    with col2:
        if comparable_properties:
            avg_days_on_market = 45  # Placeholder - would need actual DOM data
            inventory_months = 3.2   # Placeholder - would need actual inventory data
            
            st.markdown(f"""
            <div class="feature-card">
                <h4>⏱️ Market Timing</h4>
                <p><strong>Avg Days on Market:</strong> {avg_days_on_market} days</p>
                <p><strong>Inventory Months:</strong> {inventory_months} months</p>
                <p><strong>Market Type:</strong> {'Seller\'s Market' if inventory_months < 4 else 'Buyer\'s Market'}</p>
            </div>
            """, unsafe_allow_html=True)
    
    with col3:
        if price_data:
            # Calculate price appreciation
            if len(price_data) > 1:
                start_price = price_data[0]["price"]
                end_price = price_data[-1]["price"]
                time_diff = (price_data[-1]["date"] - price_data[0]["date"]).days / 365.25
                
                if time_diff > 0:
                    annual_appreciation = ((end_price / start_price) ** (1 / time_diff) - 1) * 100
                else:
                    annual_appreciation = 0
            else:
                annual_appreciation = 0
            
            appreciation_color = "green" if annual_appreciation > 3 else "orange" if annual_appreciation > 0 else "red"
            
            st.markdown(f"""
            <div class="feature-card">
                <h4>📈 Price Trends</h4>
                <p><strong>Annual Appreciation:</strong> <span style="color: {appreciation_color}">{annual_appreciation:.1f}%</span></p>
                <p><strong>Market Trend:</strong> {'Rising' if annual_appreciation > 2 else 'Stable' if annual_appreciation > -2 else 'Declining'}</p>
                <p><strong>Investment Grade:</strong> {'A' if annual_appreciation > 5 else 'B' if annual_appreciation > 2 else 'C'}</p>
            </div>
            """, unsafe_allow_html=True)

def display_advanced_analytics(property_data: Dict[str, Any], comparable_properties: List[Dict[str, Any]]):
    """Display advanced analytics and insights"""
    st.markdown('<div class="sub-header">🔬 Advanced Analytics</div>', unsafe_allow_html=True)
    
    # Property scoring system
    st.markdown("### 🎯 Property Investment Score")
    
    score_components = calculate_property_score(property_data, comparable_properties)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        total_score = sum(score_components.values())
        max_score = len(score_components) * 10
        score_percentage = (total_score / max_score) * 100
        
        # Score color based on percentage
        if score_percentage >= 80:
            score_color = "green"
            score_grade = "A"
        elif score_percentage >= 70:
            score_color = "orange"
            score_grade = "B"
        elif score_percentage >= 60:
            score_color = "yellow"
            score_grade = "C"
        else:
            score_color = "red"
            score_grade = "D"
        
        st.markdown(f"""
        <div class="investment-card">
            <h3 style="color: {score_color}">Overall Score: {score_percentage:.0f}% (Grade {score_grade})</h3>
            <p><strong>Total Points:</strong> {total_score:.1f}/{max_score}</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        # Score breakdown
        st.markdown("**Score Breakdown:**")
        for component, score in score_components.items():
            st.write(f"• {component}: {score:.1f}/10")
    
    with col3:
        # Investment recommendation
        if score_percentage >= 80:
            recommendation = "🟢 Strong Buy - Excellent investment opportunity"
        elif score_percentage >= 70:
            recommendation = "🟡 Buy - Good investment with some considerations"
        elif score_percentage >= 60:
            recommendation = "🟠 Hold/Consider - Marginal investment"
        else:
            recommendation = "🔴 Avoid - Poor investment opportunity"
        
        st.markdown(f"""
        <div class="warning-card">
            <h4>Investment Recommendation</h4>
            <p>{recommendation}</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Risk analysis
    st.markdown("### ⚠️ Risk Analysis")
    
    risks = analyze_investment_risks(property_data, comparable_properties)
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Identified Risks:**")
        for risk in risks["high_risks"]:
            st.error(f"🔴 {risk}")
        for risk in risks["medium_risks"]:
            st.warning(f"🟡 {risk}")
        for risk in risks["low_risks"]:
            st.info(f"🟢 {risk}")
    
    with col2:
        st.markdown("**Risk Mitigation Strategies:**")
        for strategy in risks["mitigation_strategies"]:
            st.write(f"• {strategy}")
    
    # Market comparison
    if comparable_properties:
        st.markdown("### 📊 Competitive Analysis")
        
        target_price = property_data.get("lastSalePrice", 0)
        target_sqft = property_data.get("squareFootage", 0)
        
        if target_price > 0 and target_sqft > 0:
            target_price_per_sqft = target_price / target_sqft
            
            comp_prices_per_sqft = []
            for prop in comparable_properties:
                if prop.get("lastSalePrice") and prop.get("squareFootage"):
                    if prop["squareFootage"] > 0:
                        comp_prices_per_sqft.append(prop["lastSalePrice"] / prop["squareFootage"])
            
            if comp_prices_per_sqft:
                avg_comp_price_per_sqft = np.mean(comp_prices_per_sqft)
                price_difference = target_price_per_sqft - avg_comp_price_per_sqft
                price_difference_percent = (price_difference / avg_comp_price_per_sqft) * 100
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("Target Property $/Sq Ft", f"${target_price_per_sqft:.2f}")
                
                with col2:
                    st.metric("Market Average $/Sq Ft", f"${avg_comp_price_per_sqft:.2f}")
                
                with col3:
                    delta_color = "red" if price_difference > 0 else "green"
                    st.metric(
                        "Price Difference", 
                        f"${price_difference:.2f}",
                        delta=f"{price_difference_percent:.1f}%"
                    )
                
                # Value assessment
                if price_difference_percent < -10:
                    value_assessment = "🟢 Undervalued - Great deal!"
                elif price_difference_percent < 5:
                    value_assessment = "🟡 Fair Value - Market rate"
                else:
                    value_assessment = "🔴 Overvalued - Consider negotiating"
                
                st.info(f"**Value Assessment:** {value_assessment}")

def calculate_property_score(property_data: Dict[str, Any], comparable_properties: List[Dict[str, Any]]) -> Dict[str, float]:
    """Calculate comprehensive property investment score"""
    scores = {}
    
    # Location score (based on comparable properties availability)
    if len(comparable_properties) >= 10:
        scores["Location Liquidity"] = 9.0
    elif len(comparable_properties) >= 5:
        scores["Location Liquidity"] = 7.0
    else:
        scores["Location Liquidity"] = 5.0
    
    # Property age score
    year_built = property_data.get("yearBuilt")
    if year_built:
        property_age = datetime.now().year - int(year_built)
        if property_age < 10:
            scores["Property Age"] = 9.0
        elif property_age < 20:
            scores["Property Age"] = 8.0
        elif property_age < 30:
            scores["Property Age"] = 7.0
        elif property_age < 50:
            scores["Property Age"] = 6.0
        else:
            scores["Property Age"] = 4.0
    else:
        scores["Property Age"] = 5.0
    
    # Size score
    sqft = property_data.get("squareFootage", 0)
    if sqft >= 2000:
        scores["Property Size"] = 8.0
    elif sqft >= 1500:
        scores["Property Size"] = 7.0
    elif sqft >= 1000:
        scores["Property Size"] = 6.0
    else:
        scores["Property Size"] = 5.0
    
    # Price competitiveness
    if comparable_properties:
        target_price = property_data.get("lastSalePrice", 0)
        comp_prices = [p.get("lastSalePrice", 0) for p in comparable_properties if p.get("lastSalePrice")]
        
        if comp_prices and target_price > 0:
            avg_comp_price = np.mean(comp_prices)
            price_ratio = target_price / avg_comp_price
            
            if price_ratio < 0.9:
                scores["Price Competitiveness"] = 9.0
            elif price_ratio < 1.0:
                scores["Price Competitiveness"] = 8.0
            elif price_ratio < 1.1:
                scores["Price Competitiveness"] = 7.0
            else:
                scores["Price Competitiveness"] = 5.0
        else:
            scores["Price Competitiveness"] = 6.0
    else:
        scores["Price Competitiveness"] = 6.0
    
    # Condition score (based on available data)
    if property_data.get("yearBuilt") and int(property_data["yearBuilt"]) > 2000:
        scores["Property Condition"] = 8.0
    else:
        scores["Property Condition"] = 6.0
    
    return scores

def analyze_investment_risks(property_data: Dict[str, Any], comparable_properties: List[Dict[str, Any]]) -> Dict[str, List[str]]:
    """Analyze investment risks"""
    risks = {
        "high_risks": [],
        "medium_risks": [],
        "low_risks": [],
        "mitigation_strategies": []
    }
    
    # Age-related risks
    year_built = property_data.get("yearBuilt")
    if year_built and int(year_built) < 1980:
        risks["high_risks"].append("Property built before 1980 - potential lead paint/asbestos issues")
        risks["mitigation_strategies"].append("Conduct thorough property inspection")
    elif year_built and int(year_built) < 2000:
        risks["medium_risks"].append("Older property may require more maintenance")
        risks["mitigation_strategies"].append("Budget extra for maintenance and repairs")
    
    # Market liquidity risks
    if len(comparable_properties) < 5:
        risks["high_risks"].append("Limited comparable sales - low market liquidity")
        risks["mitigation_strategies"].append("Consider longer holding period")
    elif len(comparable_properties) < 10:
        risks["medium_risks"].append("Moderate market activity")
    else:
        risks["low_risks"].append("Active market with good liquidity")
    
    # Price risks
    if comparable_properties:
        prices = [p.get("lastSalePrice", 0) for p in comparable_properties if p.get("lastSalePrice")]
        if prices:
            price_std = np.std(prices)
            price_mean = np.mean(prices)
            cv = (price_std / price_mean) * 100 if price_mean > 0 else 0
            
            if cv > 30:
                risks["high_risks"].append("High price volatility in neighborhood")
                risks["mitigation_strategies"].append("Consider conservative valuation approach")
            elif cv > 20:
                risks["medium_risks"].append("Moderate price volatility")
            else:
                risks["low_risks"].append("Stable pricing in neighborhood")
    
    # Property type risks
    property_type = property_data.get("propertyType", "").lower()
    if "condo" in property_type or "townhouse" in property_type:
        risks["medium_risks"].append("HOA fees and restrictions may apply")
        risks["mitigation_strategies"].append("Review HOA documents and fee history")
    
    # General mitigation strategies
    risks["mitigation_strategies"].extend([
        "Maintain adequate insurance coverage",
        "Build cash reserves for unexpected expenses",
        "Consider professional property management",
        "Regular property maintenance and inspections"
    ])
    
    return risks

def display_export_options(property_data: Dict[str, Any], search_type: str):
    """Display comprehensive export options"""
    st.markdown('<div class="sub-header">💾 Export & Save Options</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # CSV export
        df = create_comprehensive_dataframe(property_data)
        csv = df.to_csv(index=False)
        st.download_button(
            label="📊 Download CSV",
            data=csv,
            file_name=f"property_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    
    with col2:
        # JSON export
        json_str = json.dumps(property_data, indent=2, default=str)
        st.download_button(
            label="📄 Download JSON",
            data=json_str,
            file_name=f"property_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json"
        )
    
    with col3:
        # PDF report (placeholder)
        if st.button("📋 Generate PDF Report"):
            st.info("PDF report generation feature coming soon!")
    
    with col4:
        # Email report (placeholder)
        if st.button("📧 Email Report"):
            st.info("Email report feature coming soon!")

def create_comprehensive_dataframe(property_data: Dict[str, Any]) -> pd.DataFrame:
    """Create comprehensive DataFrame for export"""
    flat_data = {}
    
    # Basic property information
    basic_fields = [
        'id', 'formattedAddress', 'addressLine1', 'city', 'state', 'zipCode',
        'county', 'propertyType', 'bedrooms', 'bathrooms', 'squareFootage',
        'lotSize', 'yearBuilt', 'lastSaleDate', 'lastSalePrice', 'ownerOccupied',
        'zoning', 'subdivision', 'assessorID'
    ]
    
    for field in basic_fields:
        flat_data[field] = property_data.get(field)
    
    # Calculated fields
    if property_data.get("lastSalePrice") and property_data.get("squareFootage"):
        if property_data["squareFootage"] > 0:
            flat_data['price_per_sqft'] = property_data["lastSalePrice"] / property_data["squareFootage"]
    
    if property_data.get("yearBuilt"):
        flat_data['property_age'] = datetime.now().year - int(property_data["yearBuilt"])
    
    # Features
    features = property_data.get('features', {})
    for key, value in features.items():
        flat_data[f'feature_{key}'] = value
    
    # HOA information
    hoa = property_data.get('hoa', {})
    if hoa:
        flat_data['hoa_fee'] = hoa.get('fee')
        flat_data['hoa_frequency'] = hoa.get('frequency')
    
    # Owner information
    owner = property_data.get('owner', {})
    if owner:
        flat_data['owner_names'] = ', '.join(owner.get('names', []))
        flat_data['owner_type'] = owner.get('type')
    
    # Tax information
    tax_assessments = property_data.get('taxAssessments', {})
    if tax_assessments:
        latest_year = max(tax_assessments.keys())
        latest_assessment = tax_assessments[latest_year]
        flat_data['latest_assessment_year'] = latest_year
        flat_data['latest_assessment_total'] = latest_assessment.get('total')
        flat_data['latest_assessment_land'] = latest_assessment.get('land')
        flat_data['latest_assessment_improvements'] = latest_assessment.get('improvements')
    
    property_taxes = property_data.get('propertyTaxes', {})
    if property_taxes:
        latest_year = max(property_taxes.keys())
        latest_tax = property_taxes[latest_year]
        flat_data['latest_tax_year'] = latest_year
        flat_data['latest_tax_total'] = latest_tax.get('total')
    
    # Add timestamp
    flat_data['analysis_date'] = datetime.now().isoformat()
    
    return pd.DataFrame([flat_data])

def generate_property_report(property_data: Dict[str, Any], search_type: str):
    """Generate comprehensive property report"""
    st.markdown('<div class="sub-header">📋 Property Analysis Report</div>', unsafe_allow_html=True)
    
    report_content = f"""
    # Property Analysis Report
    
    **Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    **Analysis Type:** {search_type}
    **Property Address:** {property_data.get('formattedAddress', 'N/A')}
    
    ## Executive Summary
    
    This comprehensive analysis provides detailed insights into the property located at {property_data.get('formattedAddress', 'the specified address')}. 
    The analysis includes property characteristics, market comparisons, investment potential, and risk assessment.
    
    ## Property Details
    
    - **Property Type:** {property_data.get('propertyType', 'N/A')}
    - **Bedrooms:** {property_data.get('bedrooms', 'N/A')}
    - **Bathrooms:** {property_data.get('bathrooms', 'N/A')}
    - **Square Footage:** {format_number(property_data.get('squareFootage'))}
    - **Lot Size:** {format_number(property_data.get('lotSize'))}
    - **Year Built:** {property_data.get('yearBuilt', 'N/A')}
    - **Last Sale Price:** {format_currency(property_data.get('lastSalePrice'))}
    - **Last Sale Date:** {property_data.get('lastSaleDate', 'N/A')[:10] if property_data.get('lastSaleDate') else 'N/A'}
    
    ## Investment Analysis
    
    [Investment analysis would be included here based on the calculations performed]
    
    ## Market Comparison
    
    [Market comparison data would be included here]
    
    ## Risk Assessment
    
    [Risk assessment would be included here]
    
    ## Recommendations
    
    [Investment recommendations would be included here]
    
    ---
    
    *This report was generated by the Enhanced RentCast Real Estate Analytics Platform*
    """
    
    st.markdown(report_content)
    
    # Download report as text file
    st.download_button(
        label="📥 Download Report",
        data=report_content,
        file_name=f"property_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md",
        mime="text/markdown"
    )

# Utility functions
def format_currency(amount: Optional[int]) -> str:
    """Format currency values"""
    if amount is None or amount == 0:
        return "N/A"
    return f"${amount:,}"

def format_number(number: Optional[int]) -> str:
    """Format numeric values"""
    if number is None or number == 0:
        return "N/A"
    return f"{number:,}"

def main():
    """Enhanced main application with robust Supabase integration"""
    st.set_page_config(
        page_title="WordPress Auth Manager",
        page_icon="🔐",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    with st.sidebar:
        st.markdown("### 🔧 Supabase Configuration")
        
        supabase_url = st.text_input(
            "Supabase URL", 
            value=st.session_state.get("supabase_url", ""),
            placeholder="https://your-project.supabase.co",
            help="Your Supabase project URL (must start with https://)"
        )
        
        supabase_anon_key = st.text_input(
            "Supabase Anon Key", 
            value=st.session_state.get("supabase_anon_key", ""),
            type="password",
            placeholder="eyJ...",
            help="Your Supabase anonymous key"
        )
        
        st.markdown("### 🔑 API Configuration")
        consumer_secret = st.text_input(
            "Consumer Secret",
            value=st.session_state.get("consumer_secret", ""),
            type="password",
            placeholder="Enter consumer secret for subscription API",
            help="Required for retrieving subscriptions from WordPress API"
        )
        
        # Store in session state
        if supabase_url:
            st.session_state.supabase_url = supabase_url
        if supabase_anon_key:
            st.session_state.supabase_anon_key = supabase_anon_key
        if consumer_secret:
            st.session_state.consumer_secret = consumer_secret
        
        if st.button("🔗 Test Supabase Connection"):
            if supabase_url and supabase_anon_key:
                if not supabase_url.startswith(('http://', 'https://')):
                    st.error("❌ Invalid URL format. URL must start with http:// or https://")
                elif not supabase_url.endswith('.supabase.co') and 'supabase' not in supabase_url:
                    st.error("❌ Invalid Supabase URL. Please use your project's Supabase URL")
                else:
                    with st.spinner("Testing connection..."):
                        try:
                            test_client = create_client(supabase_url, supabase_anon_key)
                            test_client.table("wp_users").select("count", count="exact").limit(1).execute()
                            st.success("✅ Connection successful!")
                        except Exception as e:
                            error_msg = str(e)
                            if "Invalid API key" in error_msg:
                                st.error("❌ Invalid API key")
                            elif "not found" in error_msg.lower() or "Invalid URL" in error_msg:
                                st.error("❌ Project not found or invalid URL")
                            elif "Failed to establish a new connection" in error_msg:
                                st.error("❌ Network connection failed")
                            else:
                                st.error(f"❌ Connection failed: {error_msg}")
            else:
                st.warning("Please enter both URL and Anon Key")
        
        st.markdown("---")
        st.markdown("### 📊 Database Setup")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 Auto-Setup Database"):
                if supabase_url and supabase_anon_key:
                    temp_manager = SupabaseManager(supabase_url, supabase_anon_key)
                    if temp_manager.is_connected():
                        temp_manager.create_tables_if_not_exist()
                    else:
                        st.error("❌ Cannot connect to Supabase")
                else:
                    st.warning("Configure Supabase connection first")
        
        with col2:
            if st.button("📋 Check Tables Only"):
                if supabase_url and supabase_anon_key:
                    temp_manager = SupabaseManager(supabase_url, supabase_anon_key)
                    if temp_manager.is_connected():
                        # Just check without creating
                        tables_to_check = [
                            "wp_users", "user_usage", "property_searches", 
                            "property_watchlist", "analysis_reports", "auth_sessions"
                        ]
                        missing_tables = []
                        for table in tables_to_check:
                            try:
                                temp_manager.client.table(table).select("*").limit(1).execute()
                            except Exception:
                                missing_tables.append(table)
                        
                        if missing_tables:
                            st.warning(f"⚠️ Missing tables: {', '.join(missing_tables)}")
                        else:
                            st.success("✅ All tables exist")
                else:
                    st.warning("Configure Supabase connection first")
    
    supabase_manager = None
    if st.session_state.get("supabase_url") and st.session_state.get("supabase_anon_key"):
        supabase_manager = SupabaseManager(
            st.session_state.supabase_url, 
            st.session_state.supabase_anon_key
        )
        
        if supabase_manager.is_connected():
            supabase_manager.create_tables_if_not_exist()
    
    wp_auth = WordPressAuthManager()
    
    if not st.session_state.get("authenticated", False):
        render_wordpress_auth(wp_auth)
    else:
        # Main application interface
        user_data = st.session_state.get("user_data", {})
        
        # Header with user info
        col1, col2, col3 = st.columns([2, 1, 1])
        with col1:
            st.markdown(f"### Welcome, {st.session_state.get('username', 'User')}!")
            st.markdown(f"**Role:** {user_data.get('role', 'subscriber').title()}")
        
        with col2:
            if user_data.get('status'):
                st.success(f"Status: {user_data['status'].title()}")
        
        with col3:
            if st.button("🚪 Sign Out"):
                for key in list(st.session_state.keys()):
                    if key.startswith(('authenticated', 'user_data', 'username', 'password')):
                        del st.session_state[key]
                st.rerun()
        
        if supabase_manager and supabase_manager.is_connected():
            # Sync user data with Supabase
            wp_auth.sync_user_data(supabase_manager, user_data)
            render_enhanced_dashboard(user_data, supabase_manager)
        else:
            st.warning("⚠️ Supabase not configured. Please configure Supabase in the sidebar to access full functionality.")
            st.info("You can still use WordPress authentication features.")
            
            # Show basic user info without database features
            st.markdown("### 📋 User Information")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Username:** {user_data.get('user_name', 'N/A')}")
                st.write(f"**Role:** {user_data.get('role', 'N/A')}")
            with col2:
                st.write(f"**Status:** {user_data.get('status', 'N/A')}")
                st.write(f"**Product:** {user_data.get('product_name', 'N/A')}")

    # Footer
    st.markdown("---")
    username = user_data.get("user_name", "User")
    role = user_data.get("role", "subscriber")
    product = user_data.get("product_name", "N/A")
    
    st.markdown(f"""
    <div style="text-align: center; padding: 2rem; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 15px; color: white; margin-top: 2rem;">
        <h3>🏠 Enhanced RentCast Real Estate Analytics Platform</h3>
        <p>Built with ❤️ using Streamlit • Powered by RentCast API • WordPress Integration</p>
        <p><strong>Logged in as:</strong> {username} ({role}) • <strong>Subscription:</strong> {product}</p>
        <p><em>Your comprehensive real estate investment analysis solution</em></p>
    </div>
    """, unsafe_allow_html=True)

def apply_custom_css():
    """Apply custom CSS styling"""
    st.markdown("""
    <style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 2rem;
    }
    
    .sub-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #2c3e50;
        margin: 1rem 0;
        padding: 0.5rem 0;
        border-bottom: 2px solid #3498db;
    }
    
    .analysis-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
        border-left: 5px solid #3498db;
    }
    
    .stButton > button {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        transition: all 0.3s ease;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 5px 15px rgba(0,0,0,0.2);
    }
    </style>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
