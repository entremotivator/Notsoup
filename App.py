import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import hashlib
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from typing import Dict, Any, Optional, List
import time
from gotrue.errors import AuthApiError
import numpy as np

# Page configuration
st.set_page_config(
    page_title="Real Estate Investment Analyzer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Enhanced CSS for better styling
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
    }
    
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 15px;
        color: white;
        margin: 0.5rem 0;
        box-shadow: 0 8px 32px rgba(0,0,0,0.1);
    }
    
    .property-card {
        background: white;
        padding: 1.5rem;
        border-radius: 15px;
        border: 1px solid #e0e0e0;
        margin: 1rem 0;
        box-shadow: 0 4px 16px rgba(0,0,0,0.1);
        transition: transform 0.2s;
    }
    
    .property-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.15);
    }
    
    .investor-metric {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        margin: 0.5rem;
    }
    
    .warning-card {
        background: linear-gradient(135deg, #ff9a9e 0%, #fecfef 100%);
        padding: 1rem;
        border-radius: 10px;
        color: #333;
        margin: 1rem 0;
    }
    
    .success-card {
        background: linear-gradient(135deg, #a8edea 0%, #fed6e3 100%);
        padding: 1rem;
        border-radius: 10px;
        color: #333;
        margin: 1rem 0;
    }
    
    .sidebar .sidebar-content {
        background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
    }
    
    .stAlert > div {
        padding-top: 0.5rem;
    }
    
    .dashboard-section {
        background: #f8f9fa;
        padding: 2rem;
        border-radius: 15px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

class RentCastAPI:
    """Enhanced RentCast API client with comprehensive data retrieval"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.rentcast.io/v1"
        self.headers = {
            "accept": "application/json",
            "X-Api-Key": api_key
        }
    
    def search_properties(self, address: str) -> Dict[str, Any]:
        """Search for properties by address"""
        url = f"{self.base_url}/properties"
        params = {"address": address}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"API Error: {str(e)}")
            return {}
    
    def get_rent_estimate(self, address: str) -> Dict[str, Any]:
        """Get rent estimate for a property"""
        url = f"{self.base_url}/rent-estimate"
        params = {"address": address}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Rent Estimate API Error: {str(e)}")
            return {}
    
    def get_market_data(self, city: str, state: str) -> Dict[str, Any]:
        """Get market data for a city"""
        url = f"{self.base_url}/markets"
        params = {"city": city, "state": state}
        
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            st.error(f"Market Data API Error: {str(e)}")
            return {}

class SupabaseManager:
    """Enhanced Supabase client with additional functionality"""
    
    def __init__(self, url: str, key: str):
        self.client: Client = create_client(url, key)
    
    def sign_up(self, email: str, password: str) -> Dict[str, Any]:
        """Sign up a new user"""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            return {"success": True, "user": response.user, "session": response.session}
        except AuthApiError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def sign_in(self, email: str, password: str) -> Dict[str, Any]:
        """Sign in an existing user"""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return {"success": True, "user": response.user, "session": response.session}
        except AuthApiError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def sign_out(self) -> bool:
        """Sign out the current user"""
        try:
            self.client.auth.sign_out()
            return True
        except Exception as e:
            st.error(f"Sign out error: {str(e)}")
            return False
    
    def get_current_user(self):
        """Get the current authenticated user"""
        try:
            return self.client.auth.get_user()
        except Exception:
            return None
    
    def reset_password(self, email: str) -> Dict[str, Any]:
        """Send password reset email"""
        try:
            self.client.auth.reset_password_email(email)
            return {"success": True}
        except AuthApiError as e:
            return {"success": False, "error": str(e)}
        except Exception as e:
            return {"success": False, "error": f"Unexpected error: {str(e)}"}
    
    def get_user_usage(self, user_id: str) -> int:
        """Get current month's API usage for user"""
        current_month = datetime.now().strftime("%Y-%m")
        
        try:
            result = self.client.table("user_usage").select("*").eq("user_id", user_id).eq("month", current_month).execute()
            
            if result.data:
                return result.data[0]["usage_count"]
            else:
                self.client.table("user_usage").insert({
                    "user_id": user_id,
                    "month": current_month,
                    "usage_count": 0
                }).execute()
                return 0
        except Exception as e:
            st.error(f"Database error: {str(e)}")
            return 0
    
    def increment_usage(self, user_id: str) -> bool:
        """Increment user's API usage count"""
        current_month = datetime.now().strftime("%Y-%m")
        current_usage = self.get_user_usage(user_id)
        
        if current_usage >= 100:  # Increased limit
            return False
        
        try:
            self.client.table("user_usage").update({
                "usage_count": current_usage + 1
            }).eq("user_id", user_id).eq("month", current_month).execute()
            return True
        except Exception as e:
            st.error(f"Failed to update usage: {str(e)}")
            return False
    
    def save_property_data(self, user_id: str, property_data: Dict[str, Any], analysis_data: Dict[str, Any] = None):
        """Save property data and analysis to database"""
        try:
            self.client.table("property_searches").insert({
                "user_id": user_id,
                "property_data": property_data,
                "analysis_data": analysis_data or {},
                "search_date": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            st.error(f"Failed to save data: {str(e)}")
    
    def get_user_searches(self, user_id: str, limit: int = 20) -> list:
        """Get recent property searches for user"""
        try:
            result = self.client.table("property_searches").select("*").eq("user_id", user_id).order("search_date", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            st.error(f"Failed to fetch search history: {str(e)}")
            return []
    
    def save_investment_analysis(self, user_id: str, property_id: str, analysis: Dict[str, Any]):
        """Save investment analysis"""
        try:
            self.client.table("investment_analyses").insert({
                "user_id": user_id,
                "property_id": property_id,
                "analysis": analysis,
                "created_date": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            st.error(f"Failed to save analysis: {str(e)}")

class InvestmentCalculator:
    """Comprehensive investment analysis calculator"""
    
    @staticmethod
    def calculate_cash_flow(monthly_rent: float, monthly_expenses: float) -> float:
        """Calculate monthly cash flow"""
        return monthly_rent - monthly_expenses
    
    @staticmethod
    def calculate_cap_rate(noi: float, property_value: float) -> float:
        """Calculate capitalization rate"""
        if property_value == 0:
            return 0
        return (noi / property_value) * 100
    
    @staticmethod
    def calculate_cash_on_cash_return(annual_cash_flow: float, cash_invested: float) -> float:
        """Calculate cash-on-cash return"""
        if cash_invested == 0:
            return 0
        return (annual_cash_flow / cash_invested) * 100
    
    @staticmethod
    def calculate_roi(annual_profit: float, total_investment: float) -> float:
        """Calculate return on investment"""
        if total_investment == 0:
            return 0
        return (annual_profit / total_investment) * 100
    
    @staticmethod
    def calculate_debt_service_coverage_ratio(noi: float, annual_debt_service: float) -> float:
        """Calculate debt service coverage ratio"""
        if annual_debt_service == 0:
            return float('inf')
        return noi / annual_debt_service
    
    @staticmethod
    def calculate_gross_rent_multiplier(property_value: float, annual_rent: float) -> float:
        """Calculate gross rent multiplier"""
        if annual_rent == 0:
            return 0
        return property_value / annual_rent
    
    @staticmethod
    def calculate_break_even_ratio(operating_expenses: float, debt_service: float, gross_income: float) -> float:
        """Calculate break-even ratio"""
        if gross_income == 0:
            return 0
        return ((operating_expenses + debt_service) / gross_income) * 100

def render_auth_page(supabase_manager: SupabaseManager):
    """Enhanced authentication page"""
    st.markdown('<h1 class="main-header">🏠 Real Estate Investment Analyzer</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        tab1, tab2, tab3 = st.tabs(["🔑 Sign In", "📝 Sign Up", "🔄 Reset Password"])
        
        with tab1:
            st.markdown("### Welcome Back!")
            with st.form("sign_in_form"):
                email = st.text_input("📧 Email Address", key="signin_email")
                password = st.text_input("🔒 Password", type="password", key="signin_password")
                submit_signin = st.form_submit_button("Sign In", type="primary", use_container_width=True)
                
                if submit_signin:
                    if not email or not password:
                        st.error("Please fill in all fields.")
                    else:
                        with st.spinner("Signing in..."):
                            result = supabase_manager.sign_in(email, password)
                            if result["success"]:
                                st.session_state.user = result["user"]
                                st.session_state.authenticated = True
                                st.success("Successfully signed in!")
                                st.rerun()
                            else:
                                st.error(f"Sign in failed: {result['error']}")
        
        with tab2:
            st.markdown("### Create Your Account")
            with st.form("sign_up_form"):
                email = st.text_input("📧 Email Address", key="signup_email")
                password = st.text_input("🔒 Password", type="password", key="signup_password", 
                                       help="Password should be at least 6 characters long")
                confirm_password = st.text_input("🔒 Confirm Password", type="password", key="confirm_password")
                submit_signup = st.form_submit_button("Create Account", type="primary", use_container_width=True)
                
                if submit_signup:
                    if not email or not password or not confirm_password:
                        st.error("Please fill in all fields.")
                    elif password != confirm_password:
                        st.error("Passwords do not match.")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters long.")
                    else:
                        with st.spinner("Creating account..."):
                            result = supabase_manager.sign_up(email, password)
                            if result["success"]:
                                if result["user"]:
                                    st.session_state.user = result["user"]
                                    st.session_state.authenticated = True
                                    st.success("Account created successfully! Welcome!")
                                    st.rerun()
                                else:
                                    st.success("Account created! Please check your email to confirm your account.")
                            else:
                                st.error(f"Sign up failed: {result['error']}")
        
        with tab3:
            st.markdown("### Reset Your Password")
            with st.form("reset_password_form"):
                email = st.text_input("📧 Email Address", key="reset_email", 
                                     help="Enter your email to receive a password reset link")
                submit_reset = st.form_submit_button("Send Reset Email", type="secondary", use_container_width=True)
                
                if submit_reset:
                    if not email:
                        st.error("Please enter your email address.")
                    else:
                        with st.spinner("Sending reset email..."):
                            result = supabase_manager.reset_password(email)
                            if result["success"]:
                                st.success("Password reset email sent! Please check your inbox.")
                            else:
                                st.error(f"Reset failed: {result['error']}")
    
    # Feature highlights
    st.markdown("---")
    st.markdown("### 🚀 Platform Features")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown("""
        <div class="property-card">
            <h4>🏠 Property Analysis</h4>
            <p>Comprehensive property data and market insights</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown("""
        <div class="property-card">
            <h4>📊 Investment Metrics</h4>
            <p>ROI, Cap Rate, Cash Flow calculations</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown("""
        <div class="property-card">
            <h4>📈 Market Data</h4>
            <p>Real-time market trends and comparables</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        st.markdown("""
        <div class="property-card">
            <h4>💾 Portfolio Tracking</h4>
            <p>Save and track your investment properties</p>
        </div>
        """, unsafe_allow_html=True)

def render_enhanced_dashboard(user, supabase_manager: SupabaseManager):
    """Enhanced dashboard with comprehensive analytics"""
    st.markdown('<h1 class="main-header">📊 Investment Dashboard</h1>', unsafe_allow_html=True)
    
    user_id = user.id
    current_usage = supabase_manager.get_user_usage(user_id)
    remaining_searches = 100 - current_usage
    recent_searches = supabase_manager.get_user_searches(user_id, limit=10)
    
    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🔍 {current_usage}</h3>
            <p>Searches Used</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>⚡ {remaining_searches}</h3>
            <p>Searches Remaining</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        st.markdown(f"""
        <div class="metric-card">
            <h3>🏠 {len(recent_searches)}</h3>
            <p>Properties Analyzed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        usage_percentage = (current_usage / 100) * 100
        st.markdown(f"""
        <div class="metric-card">
            <h3>📊 {usage_percentage:.1f}%</h3>
            <p>Monthly Usage</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Usage progress
    st.progress(current_usage / 100)
    
    # Recent searches with enhanced display
    st.markdown("### 🕐 Recent Property Analyses")
    
    if recent_searches:
        for i, search in enumerate(recent_searches[:5]):
            property_data = search["property_data"]
            analysis_data = search.get("analysis_data", {})
            search_date = datetime.fromisoformat(search["search_date"].replace("Z", "+00:00"))
            
            with st.expander(f"🏠 {property_data.get('formattedAddress', 'Unknown Address')} - {search_date.strftime('%Y-%m-%d %H:%M')}"):
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.markdown("**Property Details**")
                    st.write(f"Type: {property_data.get('propertyType', 'N/A')}")
                    st.write(f"Bedrooms: {property_data.get('bedrooms', 'N/A')}")
                    st.write(f"Bathrooms: {property_data.get('bathrooms', 'N/A')}")
                    st.write(f"Sq Ft: {format_number(property_data.get('squareFootage'))}")
                
                with col2:
                    st.markdown("**Financial Data**")
                    st.write(f"Last Sale: {format_currency(property_data.get('lastSalePrice'))}")
                    st.write(f"Year Built: {property_data.get('yearBuilt', 'N/A')}")
                    if analysis_data.get('estimated_rent'):
                        st.write(f"Est. Rent: {format_currency(analysis_data['estimated_rent'])}")
                
                with col3:
                    st.markdown("**Investment Metrics**")
                    if analysis_data.get('cap_rate'):
                        st.write(f"Cap Rate: {analysis_data['cap_rate']:.2f}%")
                    if analysis_data.get('cash_flow'):
                        st.write(f"Monthly Cash Flow: {format_currency(analysis_data['cash_flow'])}")
                    if analysis_data.get('roi'):
                        st.write(f"ROI: {analysis_data['roi']:.2f}%")
        
        # Analytics charts
        if len(recent_searches) > 1:
            st.markdown("### 📈 Portfolio Analytics")
            
            # Create charts from search data
            dates = []
            property_values = []
            
            for search in recent_searches:
                property_data = search["property_data"]
                search_date = datetime.fromisoformat(search["search_date"].replace("Z", "+00:00"))
                dates.append(search_date)
                property_values.append(property_data.get('lastSalePrice', 0))
            
            if property_values and any(v > 0 for v in property_values):
                fig = px.line(x=dates, y=property_values, title="Property Values Over Time", markers=True)
                fig.update_layout(
                    xaxis_title="Date",
                    yaxis_title="Property Value ($)",
                    yaxis=dict(tickformat="$,.0f")
                )
                st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No recent searches found. Start analyzing properties to see your dashboard come to life!")
    
    return True

def format_currency(amount: Optional[int]) -> str:
    """Format currency values"""
    if amount is None or amount == 0:
        return "N/A"
    return f"${amount:,}"

def format_number(number: Optional[int]) -> str:
    """Format numeric values"""
    if number is None:
        return "N/A"
    return f"{number:,}"

def format_percentage(value: Optional[float]) -> str:
    """Format percentage values"""
    if value is None:
        return "N/A"
    return f"{value:.2f}%"

def display_property_card(property_data: Dict[str, Any], rent_estimate: Dict[str, Any] = None):
    """Display property information in an enhanced card format"""
    
    st.markdown(f"""
    <div class="property-card">
        <h2>🏠 {property_data.get('formattedAddress', 'Property Details')}</h2>
    </div>
    """, unsafe_allow_html=True)
    
    # Basic property metrics
    col1, col2, col3, col4, col5 = st.columns(5)
    
    metrics = [
        ("🏠 Property Type", property_data.get("propertyType", "N/A")),
        ("🛏️ Bedrooms", property_data.get("bedrooms", "N/A")),
        ("🚿 Bathrooms", property_data.get("bathrooms", "N/A")),
        ("📐 Square Feet", format_number(property_data.get("squareFootage"))),
        ("📅 Year Built", property_data.get("yearBuilt", "N/A"))
    ]
    
    for i, (label, value) in enumerate(metrics):
        with [col1, col2, col3, col4, col5][i]:
            st.metric(label, value)
    
    # Financial metrics
    st.markdown("### 💰 Financial Information")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("💵 Last Sale Price", format_currency(property_data.get("lastSalePrice")))
    
    with col2:
        last_sale_date = property_data.get("lastSaleDate")
        if last_sale_date:
            try:
                date_obj = datetime.fromisoformat(last_sale_date.replace("Z", "+00:00"))
                formatted_date = date_obj.strftime("%Y-%m-%d")
            except:
                formatted_date = last_sale_date[:10] if len(last_sale_date) >= 10 else last_sale_date
        else:
            formatted_date = "N/A"
        st.metric("📅 Last Sale Date", formatted_date)
    
    with col3:
        if rent_estimate and rent_estimate.get('rent'):
            st.metric("🏠 Estimated Rent", format_currency(rent_estimate['rent']))
        else:
            st.metric("🏠 Estimated Rent", "N/A")
    
    with col4:
        # Calculate price per sq ft
        price = property_data.get("lastSalePrice")
        sqft = property_data.get("squareFootage")
        if price and sqft and sqft > 0:
            price_per_sqft = price / sqft
            st.metric("💲 Price/Sq Ft", f"${price_per_sqft:.0f}")
        else:
            st.metric("💲 Price/Sq Ft", "N/A")

def display_investment_calculator(property_data: Dict[str, Any], rent_estimate: Dict[str, Any] = None):
    """Display comprehensive investment calculator"""
    
    st.markdown("### 🧮 Investment Calculator")
    
    # Input parameters
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("#### 📊 Property Financials")
        
        purchase_price = st.number_input(
            "Purchase Price ($)",
            value=property_data.get("lastSalePrice", 0),
            min_value=0,
            step=1000
        )
        
        down_payment_pct = st.slider(
            "Down Payment (%)",
            min_value=0,
            max_value=100,
            value=20,
            step=5
        )
        
        interest_rate = st.slider(
            "Interest Rate (%)",
            min_value=0.0,
            max_value=15.0,
            value=6.5,
            step=0.1
        )
        
        loan_term = st.selectbox(
            "Loan Term (years)",
            options=[15, 20, 25, 30],
            index=3
        )
        
        monthly_rent = st.number_input(
            "Monthly Rent ($)",
            value=rent_estimate.get('rent', 0) if rent_estimate else 0,
            min_value=0,
            step=50
        )
    
    with col2:
        st.markdown("#### 💸 Operating Expenses")
        
        property_tax_annual = st.number_input(
            "Annual Property Tax ($)",
            value=0,
            min_value=0,
            step=100
        )
        
        insurance_annual = st.number_input(
            "Annual Insurance ($)",
            value=1200,
            min_value=0,
            step=100
        )
        
        maintenance_pct = st.slider(
            "Maintenance (% of rent)",
            min_value=0,
            max_value=20,
            value=5,
            step=1
        )
        
        vacancy_pct = st.slider(
            "Vacancy Rate (%)",
            min_value=0,
            max_value=20,
            value=5,
            step=1
        )
        
        property_mgmt_pct = st.slider(
            "Property Management (% of rent)",
            min_value=0,
            max_value=15,
            value=8,
            step=1
        )
    
    # Calculate investment metrics
    if st.button("📊 Calculate Investment Metrics", type="primary"):
        calc = InvestmentCalculator()
        
        # Basic calculations
        down_payment = purchase_price * (down_payment_pct / 100)
        loan_amount = purchase_price - down_payment
        
        # Monthly mortgage payment
        monthly_rate = interest_rate / 100 / 12
        num_payments = loan_term * 12
        
        if monthly_rate > 0:
            monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
        else:
            monthly_mortgage = loan_amount / num_payments
        
        # Operating expenses
        monthly_property_tax = property_tax_annual / 12
        monthly_insurance = insurance_annual / 12
        monthly_maintenance = monthly_rent * (maintenance_pct / 100)
        monthly_vacancy_loss = monthly_rent * (vacancy_pct / 100)
        monthly_mgmt = monthly_rent * (property_mgmt_pct / 100)
        
        total_monthly_expenses = (monthly_mortgage + monthly_property_tax + 
                                monthly_insurance + monthly_maintenance + 
                                monthly_vacancy_loss + monthly_mgmt)
        
        effective_monthly_rent = monthly_rent - monthly_vacancy_loss
        monthly_cash_flow = effective_monthly_rent - total_monthly_expenses
        annual_cash_flow = monthly_cash_flow * 12
        
        # Investment metrics
        annual_noi = (effective_monthly_rent * 12) - ((monthly_property_tax + monthly_insurance + monthly_maintenance + monthly_mgmt) * 12)
        cap_rate = calc.calculate_cap_rate(annual_noi, purchase_price)
        cash_on_cash = calc.calculate_cash_on_cash_return(annual_cash_flow, down_payment)
        gross_rent_multiplier = calc.calculate_gross_rent_multiplier(purchase_price, monthly_rent * 12)
        
        # Display results
        st.markdown("### 📈 Investment Analysis Results")
        
        # Key metrics in colored cards
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            color = "success" if monthly_cash_flow > 0 else "error"
            st.markdown(f"""
            <div class="investor-metric">
                <h3>{format_currency(int(monthly_cash_flow))}</h3>
                <p>Monthly Cash Flow</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"""
            <div class="investor-metric">
                <h3>{cap_rate:.2f}%</h3>
                <p>Cap Rate</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col3:
            st.markdown(f"""
            <div class="investor-metric">
                <h3>{cash_on_cash:.2f}%</h3>
                <p>Cash-on-Cash Return</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col4:
            st.markdown(f"""
            <div class="investor-metric">
                <h3>{gross_rent_multiplier:.1f}</h3>
                <p>Gross Rent Multiplier</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Detailed breakdown
        st.markdown("### 📋 Detailed Financial Breakdown")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### 💰 Monthly Income")
            st.write(f"Gross Rent: {format_currency(int(monthly_rent))}")
            st.write(f"Vacancy Loss: -{format_currency(int(monthly_vacancy_loss))}")
            st.write(f"**Effective Income: {format_currency(int(effective_monthly_rent))}**")
        
        with col2:
            st.markdown("#### 💸 Monthly Expenses")
            st.write(f"Mortgage Payment: {format_currency(int(monthly_mortgage))}")
            st.write(f"Property Tax: {format_currency(int(monthly_property_tax))}")
            st.write(f"Insurance: {format_currency(int(monthly_insurance))}")
            st.write(f"Maintenance: {format_currency(int(monthly_maintenance))}")
            st.write(f"Property Management: {format_currency(int(monthly_mgmt))}")
            st.write(f"**Total Expenses: {format_currency(int(total_monthly_expenses))}**")
        
        # Investment summary
        st.markdown("### 📊 Investment Summary")
        
        summary_data = {
            "Metric": [
                "Purchase Price",
                "Down Payment",
                "Loan Amount",
                "Monthly Cash Flow",
                "Annual Cash Flow",
                "Cap Rate",
                "Cash-on-Cash Return",
                "Gross Rent Multiplier",
                "Total Cash Needed"
            ],
            "Value": [
                format_currency(int(purchase_price)),
                format_currency(int(down_payment)),
                format_currency(int(loan_amount)),
                format_currency(int(monthly_cash_flow)),
                format_currency(int(annual_cash_flow)),
                f"{cap_rate:.2f}%",
                f"{cash_on_cash:.2f}%",
                f"{gross_rent_multiplier:.1f}",
                format_currency(int(down_payment + purchase_price * 0.03))  # Assuming 3% closing costs
            ]
        }
        
        df_summary = pd.DataFrame(summary_data)
        st.dataframe(df_summary, use_container_width=True)
        
        # Investment recommendation
        st.markdown("### 🎯 Investment Recommendation")
        
        if monthly_cash_flow > 0 and cap_rate > 6 and cash_on_cash > 8:
            st.markdown("""
            <div class="success-card">
                <h4>✅ Strong Investment Opportunity</h4>
                <p>This property shows positive cash flow, good cap rate, and strong cash-on-cash returns. Consider this investment!</p>
            </div>
            """, unsafe_allow_html=True)
        elif monthly_cash_flow > 0:
            st.markdown("""
            <div class="warning-card">
                <h4>⚠️ Moderate Investment</h4>
                <p>This property has positive cash flow but may have lower returns. Analyze market conditions and growth potential.</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
            <div class="warning-card">
                <h4>❌ Negative Cash Flow</h4>
                <p>This property shows negative cash flow. Consider negotiating price, increasing rent, or looking for better opportunities.</p>
            </div>
            """, unsafe_allow_html=True)
        
        # Return analysis data for saving
        analysis_data = {
            "monthly_cash_flow": monthly_cash_flow,
            "cap_rate": cap_rate,
            "cash_on_cash_return": cash_on_cash,
            "gross_rent_multiplier": gross_rent_multiplier,
            "estimated_rent": monthly_rent,
            "purchase_price": purchase_price,
            "down_payment": down_payment,
            "roi": cash_on_cash
        }
        
        return analysis_data
    
    return None

def display_market_analysis(property_data: Dict[str, Any], rentcast_api: RentCastAPI):
    """Display market analysis and comparables"""
    
    st.markdown("### 🏙️ Market Analysis")
    
    city = property_data.get('city')
    state = property_data.get('state')
    
    if city and state:
        with st.spinner("Loading market data..."):
            market_data = rentcast_api.get_market_data(city, state)
            
            if market_data:
                st.markdown(f"#### Market Data for {city}, {state}")
                
                col1, col2, col3, col4 = st.columns(4)
                
                # Display market metrics if available
                if isinstance(market_data, dict):
                    with col1:
                        median_price = market_data.get('medianPrice')
                        st.metric("Median Home Price", format_currency(median_price) if median_price else "N/A")
                    
                    with col2:
                        median_rent = market_data.get('medianRent')
                        st.metric("Median Rent", format_currency(median_rent) if median_rent else "N/A")
                    
                    with col3:
                        price_change = market_data.get('priceChange')
                        st.metric("Price Change (YoY)", f"{price_change}%" if price_change else "N/A")
                    
                    with col4:
                        rent_change = market_data.get('rentChange')
                        st.metric("Rent Change (YoY)", f"{rent_change}%" if rent_change else "N/A")
            else:
                st.info("Market data not available for this location.")
    else:
        st.info("City and state information needed for market analysis.")

def main():
    """Enhanced main application function"""
    
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "search"
    
    # Get configuration from secrets
    try:
        api_key = st.secrets["RENTCAST_API_KEY"]
        supabase_url = st.secrets["SUPABASE_URL"]
        supabase_key = st.secrets["SUPABASE_KEY"]
    except KeyError as e:
        st.error(f"Missing configuration: {e}")
        st.info(
            """
            **Setup Instructions:**
            Add the following to your Streamlit secrets (Secrets tab in Community Cloud, or `.streamlit/secrets.toml` locally):
            
            ```toml
            RENTCAST_API_KEY = "your_rentcast_api_key"
            SUPABASE_URL = "your_supabase_url"
            SUPABASE_KEY = "your_supabase_anon_key"
            ```
            """
        )
        st.stop()
    
    # Initialize managers
    rentcast_api = RentCastAPI(api_key)
    supabase_manager = SupabaseManager(supabase_url, supabase_key)
    
    # Check authentication
    if not st.session_state.authenticated:
        render_auth_page(supabase_manager)
        return
    
    user = st.session_state.user
    
    # Sidebar navigation
    with st.sidebar:
        st.markdown("### 🏠 Navigation")
        
        if st.button("📊 Dashboard", use_container_width=True):
            st.session_state.current_page = "dashboard"
        
        if st.button("🔍 Property Search", use_container_width=True):
            st.session_state.current_page = "search"
        
        st.markdown("---")
        
        # User info
        st.markdown(f"**👤 Logged in as:**")
        st.markdown(f"{user.email}")
        
        # Usage info
        current_usage = supabase_manager.get_user_usage(user.id)
        remaining = 100 - current_usage
        
        st.markdown(f"**📊 API Usage:**")
        st.progress(current_usage / 100)
        st.markdown(f"{current_usage}/100 searches used")
        st.markdown(f"{remaining} searches remaining")
        
        st.markdown("---")
        
        if st.button("🚪 Sign Out", use_container_width=True):
            supabase_manager.sign_out()
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    # Main content based on current page
    if st.session_state.current_page == "dashboard":
        render_enhanced_dashboard(user, supabase_manager)
    
    elif st.session_state.current_page == "search":
        st.markdown('<h1 class="main-header">🔍 Property Analysis</h1>', unsafe_allow_html=True)
        
        # Check usage limit
        current_usage = supabase_manager.get_user_usage(user.id)
        if current_usage >= 100:
            st.error("You have reached your monthly search limit of 100 searches. Please try again next month.")
            return
        
        # Property search form
        with st.form("property_search"):
            st.markdown("### Enter Property Address")
            address = st.text_input(
                "🏠 Property Address",
                placeholder="e.g., 123 Main St, City, State 12345",
                help="Enter the full address including city and state for best results"
            )
            
            col1, col2 = st.columns([3, 1])
            with col1:
                search_button = st.form_submit_button("🔍 Analyze Property", type="primary", use_container_width=True)
            with col2:
                include_calculator = st.checkbox("Include Investment Calculator", value=True)
        
        if search_button and address:
            if not supabase_manager.increment_usage(user.id):
                st.error("Unable to process search. Usage limit may have been reached.")
                return
            
            with st.spinner("🔍 Searching property data..."):
                # Get property data
                property_data = rentcast_api.search_properties(address)
                
                if not property_data:
                    st.error("No property data found for this address. Please check the address and try again.")
                    return
                
                # Get rent estimate
                rent_estimate = rentcast_api.get_rent_estimate(address)
                
                # Display property information
                display_property_card(property_data, rent_estimate)
                
                # Market analysis
                display_market_analysis(property_data, rentcast_api)
                
                # Investment calculator
                analysis_data = None
                if include_calculator:
                    analysis_data = display_investment_calculator(property_data, rent_estimate)
                
                # Export options
                st.markdown("### 📤 Export Options")
                col1, col2 = st.columns(2)
                
                with col1:
                    # JSON export
                    export_data = {
                        "property_data": property_data,
                        "rent_estimate": rent_estimate,
                        "analysis_data": analysis_data,
                        "search_date": datetime.now().isoformat()
                    }
                    
                    json_str = json.dumps(export_data, indent=2, default=str)
                    st.download_button(
                        label="📄 Download JSON",
                        data=json_str,
                        file_name=f"property_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json"
                    )
                
                with col2:
                    # CSV export
                    csv_data = {
                        "Address": [property_data.get("formattedAddress", "")],
                        "Property Type": [property_data.get("propertyType", "")],
                        "Bedrooms": [property_data.get("bedrooms", "")],
                        "Bathrooms": [property_data.get("bathrooms", "")],
                        "Square Feet": [property_data.get("squareFootage", "")],
                        "Year Built": [property_data.get("yearBuilt", "")],
                        "Last Sale Price": [property_data.get("lastSalePrice", "")],
                        "Estimated Rent": [rent_estimate.get("rent", "") if rent_estimate else ""]
                    }
                    
                    if analysis_data:
                        csv_data.update({
                            "Monthly Cash Flow": [analysis_data.get("monthly_cash_flow", "")],
                            "Cap Rate": [analysis_data.get("cap_rate", "")],
                            "Cash-on-Cash Return": [analysis_data.get("cash_on_cash_return", "")]
                        })
                    
                    df_export = pd.DataFrame(csv_data)
                    csv_string = df_export.to_csv(index=False)
                    
                    st.download_button(
                        label="📊 Download CSV",
                        data=csv_string,
                        file_name=f"property_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv"
                    )
                
                # Save to database
                supabase_manager.save_property_data(user.id, property_data, analysis_data)
                
                st.success("✅ Property analysis completed and saved to your dashboard!")

if __name__ == "__main__":
    main()
