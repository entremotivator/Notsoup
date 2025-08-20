import streamlit as st
import requests
import pandas as pd
import json
from datetime import datetime, timedelta
import hashlib
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, Optional
import time
from gotrue.errors import AuthApiError

# Page configuration
st.set_page_config(
    page_title="RentCast Real Estate Data Lookup",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #1f77b4;
        margin: 0.5rem 0;
    }
    .stAlert > div {
        padding-top: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

class RentCastAPI:
    """RentCast API client with rate limiting and error handling"""
    
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

class SupabaseManager:
    """Supabase client for user management and data storage"""
    
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
                # Create new record for user
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
        
        if current_usage >= 25:
            return False
        
        try:
            self.client.table("user_usage").update({
                "usage_count": current_usage + 1
            }).eq("user_id", user_id).eq("month", current_month).execute()
            return True
        except Exception as e:
            st.error(f"Failed to update usage: {str(e)}")
            return False
    
    def save_property_data(self, user_id: str, property_data: Dict[str, Any]):
        """Save property data to database"""
        try:
            self.client.table("property_searches").insert({
                "user_id": user_id,
                "property_data": property_data,
                "search_date": datetime.now().isoformat()
            }).execute()
        except Exception as e:
            st.error(f"Failed to save data: {str(e)}")
    
    def get_user_searches(self, user_id: str, limit: int = 10) -> list:
        """Get recent property searches for user"""
        try:
            result = self.client.table("property_searches").select("*").eq("user_id", user_id).order("search_date", desc=True).limit(limit).execute()
            return result.data if result.data else []
        except Exception as e:
            st.error(f"Failed to fetch search history: {str(e)}")
            return []

def render_auth_page(supabase_manager: SupabaseManager):
    """Render authentication page with sign up and sign in options"""
    st.markdown('<h1 class="main-header">🔐 Welcome to RentCast Property Lookup</h1>', unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["Sign In", "Sign Up", "Reset Password"])
    
    with tab1:
        st.header("Sign In to Your Account")
        with st.form("sign_in_form"):
            email = st.text_input("Email Address", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_password")
            submit_signin = st.form_submit_button("Sign In", type="primary")
            
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
        st.header("Create New Account")
        with st.form("sign_up_form"):
            email = st.text_input("Email Address", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password", 
                                   help="Password should be at least 6 characters long")
            confirm_password = st.text_input("Confirm Password", type="password", key="confirm_password")
            submit_signup = st.form_submit_button("Create Account", type="primary")
            
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
        st.header("Reset Password")
        with st.form("reset_password_form"):
            email = st.text_input("Email Address", key="reset_email", 
                                 help="Enter your email to receive a password reset link")
            submit_reset = st.form_submit_button("Send Reset Email", type="secondary")
            
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
    
    st.markdown("---")
    st.info("""
    **About RentCast Property Lookup:**
    - Get comprehensive property data for any address
    - 25 free property searches per month
    - Export data as CSV or JSON
    - Save search history to your account
    """)

def render_dashboard(user, supabase_manager: SupabaseManager):
    """Render user dashboard with recent searches and account info"""
    st.sidebar.header(f"👋 Welcome, {user.email}")
    
    # Account management
    col1, col2 = st.sidebar.columns(2)
    with col1:
        if st.button("🚪 Sign Out", key="signout_btn"):
            supabase_manager.sign_out()
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
    
    with col2:
        if st.button("📊 Dashboard", key="dashboard_btn"):
            st.session_state.show_dashboard = not st.session_state.get("show_dashboard", False)
    
    # Dashboard section
    if st.session_state.get("show_dashboard", False):
        st.header("📊 Your Dashboard")
        
        # Usage statistics
        user_id = user.id
        current_usage = supabase_manager.get_user_usage(user_id)
        remaining_searches = 25 - current_usage
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Searches Used This Month", current_usage)
        with col2:
            st.metric("Searches Remaining", remaining_searches)
        with col3:
            usage_percentage = (current_usage / 25) * 100
            st.metric("Usage Percentage", f"{usage_percentage:.1f}%")
        
        # Usage progress bar
        st.progress(current_usage / 25)
        
        # Recent searches
        st.subheader("🕐 Recent Property Searches")
        recent_searches = supabase_manager.get_user_searches(user_id, limit=5)
        
        if recent_searches:
            for search in recent_searches:
                property_data = search["property_data"]
                search_date = datetime.fromisoformat(search["search_date"].replace("Z", "+00:00"))
                
                with st.expander(f"{property_data.get('formattedAddress', 'Unknown Address')} - {search_date.strftime('%Y-%m-%d %H:%M')}"):
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.write(f"**Type:** {property_data.get('propertyType', 'N/A')}")
                        st.write(f"**Bedrooms:** {property_data.get('bedrooms', 'N/A')}")
                    with col2:
                        st.write(f"**Bathrooms:** {property_data.get('bathrooms', 'N/A')}")
                        st.write(f"**Square Feet:** {format_number(property_data.get('squareFootage'))}")
                    with col3:
                        st.write(f"**Year Built:** {property_data.get('yearBuilt', 'N/A')}")
                        st.write(f"**Last Sale:** {format_currency(property_data.get('lastSalePrice'))}")
        else:
            st.info("No recent searches found. Start by searching for a property!")
        
        st.markdown("---")
        
        return True  # Dashboard is showing
    
    return False  # Dashboard is not showing

def format_currency(amount: Optional[int]) -> str:
    """Format currency values"""
    if amount is None:
        return "N/A"
    return f"${amount:,}"

def format_number(number: Optional[int]) -> str:
    """Format numeric values"""
    if number is None:
        return "N/A"
    return f"{number:,}"

def display_property_overview(property_data: Dict[str, Any]):
    """Display property overview section"""
    st.subheader("🏠 Property Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
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
        st.metric("Last Sale Date", property_data.get("lastSaleDate", "N/A")[:10] if property_data.get("lastSaleDate") else "N/A")

def display_property_features(features: Dict[str, Any]):
    """Display property features section"""
    if not features:
        return
    
    st.subheader("✨ Property Features")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("**Architecture & Structure:**")
        st.write(f"• Architecture Type: {features.get('architectureType', 'N/A')}")
        st.write(f"• Floor Count: {features.get('floorCount', 'N/A')}")
        st.write(f"• Foundation: {features.get('foundationType', 'N/A')}")
        st.write(f"• Exterior: {features.get('exteriorType', 'N/A')}")
        st.write(f"• Roof Type: {features.get('roofType', 'N/A')}")
        
        st.write("**Rooms & Spaces:**")
        st.write(f"• Total Rooms: {features.get('roomCount', 'N/A')}")
        st.write(f"• Garage: {'Yes' if features.get('garage') else 'No'}")
        st.write(f"• Garage Spaces: {features.get('garageSpaces', 'N/A')}")
    
    with col2:
        st.write("**Climate Control:**")
        st.write(f"• Heating: {'Yes' if features.get('heating') else 'No'}")
        st.write(f"• Heating Type: {features.get('heatingType', 'N/A')}")
        st.write(f"• Cooling: {'Yes' if features.get('cooling') else 'No'}")
        st.write(f"• Cooling Type: {features.get('coolingType', 'N/A')}")
        
        st.write("**Amenities:**")
        st.write(f"• Fireplace: {'Yes' if features.get('fireplace') else 'No'}")
        st.write(f"• Pool: {'Yes' if features.get('pool') else 'No'}")
        st.write(f"• View Type: {features.get('viewType', 'N/A')}")

def display_tax_information(property_data: Dict[str, Any]):
    """Display tax assessment and property tax information"""
    tax_assessments = property_data.get("taxAssessments", {})
    property_taxes = property_data.get("propertyTaxes", {})
    
    if not tax_assessments and not property_taxes:
        return
    
    st.subheader("💰 Tax Information")
    
    if tax_assessments:
        st.write("**Tax Assessments:**")
        assessment_data = []
        for year, data in tax_assessments.items():
            assessment_data.append({
                "Year": year,
                "Total Assessment": format_currency(data.get("value")),
                "Land Value": format_currency(data.get("land")),
                "Improvements": format_currency(data.get("improvements"))
            })
        
        if assessment_data:
            df_assessments = pd.DataFrame(assessment_data)
            st.dataframe(df_assessments, use_container_width=True)
    
    if property_taxes:
        st.write("**Property Taxes:**")
        tax_data = []
        for year, data in property_taxes.items():
            tax_data.append({
                "Year": year,
                "Total Tax": format_currency(data.get("total"))
            })
        
        if tax_data:
            df_taxes = pd.DataFrame(tax_data)
            st.dataframe(df_taxes, use_container_width=True)

def display_property_history(history: Dict[str, Any]):
    """Display property sale history"""
    if not history:
        return
    
    st.subheader("📈 Property History")
    
    history_data = []
    for date, data in history.items():
        history_data.append({
            "Date": date,
            "Event": data.get("event", "N/A"),
            "Price": format_currency(data.get("price"))
        })
    
    if history_data:
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True)
        
        # Create price trend chart if multiple sales
        if len(history_data) > 1:
            fig = px.line(df_history, x="Date", y=[int(str(row["Price"]).replace("$", "").replace(",", "")) for row in history_data],
                         title="Property Value Over Time")
            fig.update_layout(yaxis_title="Sale Price ($)")
            st.plotly_chart(fig, use_container_width=True)

def display_owner_information(owner_data: Dict[str, Any]):
    """Display property owner information"""
    if not owner_data:
        return
    
    st.subheader("👤 Owner Information")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.write(f"**Owner Names:** {', '.join(owner_data.get('names', []))}")
        st.write(f"**Entity Type:** {owner_data.get('type', 'N/A')}")
    
    with col2:
        mailing_address = owner_data.get('mailingAddress', {})
        if mailing_address:
            st.write(f"**Mailing Address:**")
            st.write(mailing_address.get('formattedAddress', 'N/A'))

def create_property_dataframe(property_data: Dict[str, Any]) -> pd.DataFrame:
    """Convert property data to DataFrame for CSV export"""
    flat_data = {}
    
    # Basic property info
    basic_fields = [
        'id', 'formattedAddress', 'addressLine1', 'city', 'state', 'zipCode',
        'county', 'propertyType', 'bedrooms', 'bathrooms', 'squareFootage',
        'lotSize', 'yearBuilt', 'lastSaleDate', 'lastSalePrice', 'ownerOccupied'
    ]
    
    for field in basic_fields:
        flat_data[field] = property_data.get(field)
    
    # Features
    features = property_data.get('features', {})
    for key, value in features.items():
        flat_data[f'feature_{key}'] = value
    
    # HOA
    hoa = property_data.get('hoa', {})
    if hoa:
        flat_data['hoa_fee'] = hoa.get('fee')
    
    # Owner info
    owner = property_data.get('owner', {})
    if owner:
        flat_data['owner_names'] = ', '.join(owner.get('names', []))
        flat_data['owner_type'] = owner.get('type')
    
    return pd.DataFrame([flat_data])

def main():
    """Main application function"""
    # Initialize session state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    
    # Sidebar configuration (always visible)
    st.sidebar.header("⚙️ Configuration")
    
    # API Key and Supabase configuration
    api_key = st.sidebar.text_input("RentCast API Key", type="password", help="Enter your RentCast API key")
    supabase_url = st.sidebar.text_input("Supabase URL", help="Your Supabase project URL")
    supabase_key = st.sidebar.text_input("Supabase Key", type="password", help="Your Supabase anon key")
    
    if not all([api_key, supabase_url, supabase_key]):
        st.warning("Please fill in all configuration fields in the sidebar to get started.")
        st.info("""
        **Setup Instructions:**
        1. Get your RentCast API key from https://www.rentcast.io/
        2. Create a Supabase project at https://supabase.com/
        3. Enable Authentication in Supabase Dashboard
        4. Create the following tables in your Supabase database:
           - `user_usage` (user_id: text, month: text, usage_count: int)
           - `property_searches` (user_id: text, property_data: json, search_date: timestamp)
        5. Enter your credentials in the sidebar
        """)
        return
    
    # Initialize services
    supabase_manager = SupabaseManager(supabase_url, supabase_key)
    
    # Check authentication status
    if not st.session_state.authenticated:
        # Try to get current user from Supabase session
        current_user = supabase_manager.get_current_user()
        if current_user and current_user.user:
            st.session_state.user = current_user.user
            st.session_state.authenticated = True
    
    # Render appropriate page
    if not st.session_state.authenticated:
        render_auth_page(supabase_manager)
        return
    
    # User is authenticated - render main application
    user = st.session_state.user
    
    # Render dashboard if requested
    showing_dashboard = render_dashboard(user, supabase_manager)
    
    # Don't show main search interface if dashboard is showing
    if showing_dashboard:
        return
    
    # Main application interface
    st.markdown('<h1 class="main-header">🏠 RentCast Real Estate Data Lookup</h1>', unsafe_allow_html=True)
    
    # Initialize RentCast API
    rentcast_api = RentCastAPI(api_key)
    user_id = user.id
    
    # Check rate limit
    current_usage = supabase_manager.get_user_usage(user_id)
    remaining_searches = 25 - current_usage
    
    st.sidebar.metric("Searches Remaining This Month", remaining_searches)
    
    if remaining_searches <= 0:
        st.error("You have reached your monthly limit of 25 searches. Please wait until next month.")
        return
    
    # Main search interface
    st.header("🔍 Property Search")
    
    address = st.text_input(
        "Enter Property Address",
        placeholder="e.g., 123 Main St, New York, NY 10001",
        help="Enter the full address including city, state, and zip code for best results"
    )
    
    col1, col2 = st.columns([1, 4])
    with col1:
        search_button = st.button("Search Property", type="primary")
    
    if search_button and address:
        if remaining_searches <= 0:
            st.error("Monthly search limit reached!")
            return
        
        with st.spinner("Searching property data..."):
            # Increment usage
            if not supabase_manager.increment_usage(user_id):
                st.error("Failed to update usage count. Please try again.")
                return
            
            # Search for property
            result = rentcast_api.search_properties(address)
            
            if not result:
                st.error("No data found or API error occurred.")
                return
            
            properties = result.get("properties", [])
            
            if not properties:
                st.warning("No properties found for the given address.")
                return
            
            # Display results for first property (most relevant)
            property_data = properties[0]
            
            # Save to Supabase
            supabase_manager.save_property_data(user_id, property_data)
            
            st.success(f"Found property data! Searches remaining: {remaining_searches - 1}")
            
            # Display property information
            st.header(f"📍 {property_data.get('formattedAddress', 'Property Details')}")
            
            # Property overview
            display_property_overview(property_data)
            
            # Property features
            display_property_features(property_data.get("features", {}))
            
            # Tax information
            display_tax_information(property_data)
            
            # Property history
            display_property_history(property_data.get("history", {}))
            
            # Owner information
            display_owner_information(property_data.get("owner", {}))
            
            # Location map
            if property_data.get("latitude") and property_data.get("longitude"):
                st.subheader("📍 Location")
                map_data = pd.DataFrame([{
                    "lat": property_data["latitude"],
                    "lon": property_data["longitude"]
                }])
                st.map(map_data)
            
            # Export options
            st.header("💾 Export Options")
            
            col1, col2 = st.columns(2)
            
            with col1:
                # CSV download
                df = create_property_dataframe(property_data)
                csv = df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"property_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            
            with col2:
                # JSON download
                json_str = json.dumps(property_data, indent=2)
                st.download_button(
                    label="📥 Download as JSON",
                    data=json_str,
                    file_name=f"property_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                    mime="application/json"
                )
            
            # Raw data expander
            with st.expander("🔍 View Raw Property Data"):
                st.json(property_data)
    
    # Footer
    st.markdown("---")
    st.markdown(
        f"Built with ❤️ using Streamlit • Powered by RentCast API • Logged in as: {user.email}"
    )

if __name__ == "__main__":
    main()
