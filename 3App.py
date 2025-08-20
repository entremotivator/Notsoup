import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
from supabase import create_client, Client
import plotly.express as px
import plotly.graph_objects as go

# Page configuration
st.set_page_config(
    page_title="Real Estate Investment Analyzer",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
.main-header {
    font-size: 3rem;
    font-weight: bold;
    text-align: center;
    background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    margin-bottom: 2rem;
}

.metric-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 1.5rem;
    border-radius: 15px;
    color: white;
    text-align: center;
    box-shadow: 0 8px 25px rgba(0,0,0,0.15);
    transition: transform 0.3s ease;
}

.metric-card:hover {
    transform: translateY(-5px);
}

.property-card {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    padding: 2rem;
    border-radius: 15px;
    color: white;
    margin-bottom: 2rem;
    box-shadow: 0 10px 30px rgba(0,0,0,0.3);
}

.property-detail-card {
    background: white;
    padding: 1.5rem;
    border-radius: 10px;
    margin: 1rem 0;
    box-shadow: 0 4px 15px rgba(0,0,0,0.1);
    border-left: 4px solid #667eea;
}

.feature-badge {
    background: #4CAF50;
    color: white;
    padding: 0.3rem 0.8rem;
    border-radius: 20px;
    font-size: 0.8rem;
    margin: 0.2rem;
    display: inline-block;
}

.dashboard-card {
    background: white;
    padding: 1.5rem;
    border-radius: 15px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.1);
    margin-bottom: 1rem;
    border-left: 5px solid #667eea;
}

.auth-container {
    max-width: 400px;
    margin: 0 auto;
    padding: 2rem;
    background: white;
    border-radius: 15px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}
</style>
""", unsafe_allow_html=True)

class RentCastAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.base_url = "https://api.rentcast.io/v1"
        self.headers = {
            "accept": "application/json",
            "X-Api-Key": api_key
        }
    
    def search_properties(self, address):
        """Search for property data by address"""
        try:
            url = f"{self.base_url}/properties"
            params = {"address": address}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                return data[0]
            return None
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching property data: {str(e)}")
            return None
    
    def get_rent_estimate(self, address):
        """Get rent estimate for a property"""
        try:
            url = f"{self.base_url}/rentals/rent-estimate"
            params = {"address": address}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching rent estimate: {str(e)}")
            return None
    
    def get_market_data(self, city, state):
        """Get market data for a city"""
        try:
            url = f"{self.base_url}/markets"
            params = {"city": city, "state": state}
            
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            st.error(f"Error fetching market data: {str(e)}")
            return None

class SupabaseManager:
    def __init__(self, url, key):
        self.client: Client = create_client(url, key)
    
    def sign_up(self, email, password):
        """Sign up a new user"""
        try:
            response = self.client.auth.sign_up({
                "email": email,
                "password": password
            })
            return response
        except Exception as e:
            st.error(f"Sign up error: {str(e)}")
            return None
    
    def sign_in(self, email, password):
        """Sign in an existing user"""
        try:
            response = self.client.auth.sign_in_with_password({
                "email": email,
                "password": password
            })
            return response
        except Exception as e:
            st.error(f"Sign in error: {str(e)}")
            return None
    
    def sign_out(self):
        """Sign out the current user"""
        try:
            self.client.auth.sign_out()
            return True
        except Exception as e:
            st.error(f"Sign out error: {str(e)}")
            return False
    
    def get_user_usage(self, user_id):
        """Get user's current monthly usage"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            
            response = self.client.table("user_usage").select("*").eq("user_id", user_id).eq("month", current_month).execute()
            
            if response.data:
                return response.data[0]["search_count"]
            return 0
        except Exception as e:
            st.error(f"Error getting usage: {str(e)}")
            return 0
    
    def increment_usage(self, user_id):
        """Increment user's monthly usage"""
        try:
            current_month = datetime.now().strftime("%Y-%m")
            current_usage = self.get_user_usage(user_id)
            
            if current_usage >= 100:
                return False
            
            # Check if record exists
            response = self.client.table("user_usage").select("*").eq("user_id", user_id).eq("month", current_month).execute()
            
            if response.data:
                # Update existing record
                self.client.table("user_usage").update({
                    "search_count": current_usage + 1,
                    "updated_at": datetime.now().isoformat()
                }).eq("user_id", user_id).eq("month", current_month).execute()
            else:
                # Create new record
                self.client.table("user_usage").insert({
                    "user_id": user_id,
                    "month": current_month,
                    "search_count": 1,
                    "created_at": datetime.now().isoformat(),
                    "updated_at": datetime.now().isoformat()
                }).execute()
            
            return True
        except Exception as e:
            st.error(f"Error updating usage: {str(e)}")
            return False
    
    def save_property_data(self, user_id, property_data, analysis_data=None):
        """Save property data to database"""
        try:
            data = {
                "user_id": user_id,
                "property_data": property_data,
                "analysis_data": analysis_data,
                "created_at": datetime.now().isoformat()
            }
            
            response = self.client.table("property_searches").insert(data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            st.error(f"Error saving property data: {str(e)}")
            return None
    
    def get_user_properties(self, user_id):
        """Get user's saved properties"""
        try:
            response = self.client.table("property_searches").select("*").eq("user_id", user_id).order("created_at", desc=True).execute()
            return response.data
        except Exception as e:
            st.error(f"Error getting properties: {str(e)}")
            return []
    
    def update_property_analysis(self, property_id, analysis_data):
        """Update property with new analysis data"""
        try:
            self.client.table("property_searches").update({
                "analysis_data": analysis_data,
                "updated_at": datetime.now().isoformat()
            }).eq("id", property_id).execute()
            return True
        except Exception as e:
            st.error(f"Error updating analysis: {str(e)}")
            return False

def render_auth_page(supabase_manager):
    """Render authentication page"""
    st.markdown('<h1 class="main-header">🏠 Real Estate Investment Analyzer</h1>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown('<div class="auth-container">', unsafe_allow_html=True)
        
        tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
        
        with tab1:
            st.markdown("### Welcome Back!")
            with st.form("signin_form"):
                email = st.text_input("Email", placeholder="your@email.com")
                password = st.text_input("Password", type="password")
                signin_button = st.form_submit_button("Sign In", use_container_width=True)
                
                if signin_button and email and password:
                    response = supabase_manager.sign_in(email, password)
                    if response and response.user:
                        st.session_state.authenticated = True
                        st.session_state.user = response.user
                        st.success("Successfully signed in!")
                        st.rerun()
        
        with tab2:
            st.markdown("### Create Account")
            with st.form("signup_form"):
                email = st.text_input("Email", placeholder="your@email.com", key="signup_email")
                password = st.text_input("Password", type="password", key="signup_password")
                confirm_password = st.text_input("Confirm Password", type="password")
                signup_button = st.form_submit_button("Sign Up", use_container_width=True)
                
                if signup_button and email and password:
                    if password != confirm_password:
                        st.error("Passwords do not match!")
                    elif len(password) < 6:
                        st.error("Password must be at least 6 characters!")
                    else:
                        response = supabase_manager.sign_up(email, password)
                        if response and response.user:
                            st.success("Account created! Please check your email to verify your account.")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_enhanced_dashboard(user, supabase_manager):
    """Render enhanced dashboard with analytics"""
    st.markdown('<h1 class="main-header">📊 Investment Dashboard</h1>', unsafe_allow_html=True)
    
    # Get user's properties
    properties = supabase_manager.get_user_properties(user.id)
    current_usage = supabase_manager.get_user_usage(user.id)
    
    # Dashboard metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{len(properties)}</h2>
            <p>Properties Analyzed</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h2>{current_usage}</h2>
            <p>Searches This Month</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        avg_cash_flow = 0
        if properties:
            cash_flows = [p.get('analysis_data', {}).get('monthly_cash_flow', 0) for p in properties if p.get('analysis_data')]
            avg_cash_flow = sum(cash_flows) / len(cash_flows) if cash_flows else 0
        
        st.markdown(f"""
        <div class="metric-card">
            <h2>${avg_cash_flow:,.0f}</h2>
            <p>Avg Monthly Cash Flow</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        total_investment = 0
        if properties:
            investments = [p.get('analysis_data', {}).get('down_payment', 0) for p in properties if p.get('analysis_data')]
            total_investment = sum(investments)
        
        st.markdown(f"""
        <div class="metric-card">
            <h2>${total_investment:,.0f}</h2>
            <p>Total Investment</p>
        </div>
        """, unsafe_allow_html=True)
    
    if properties:
        # Portfolio performance chart
        st.markdown("### 📈 Portfolio Performance")
        
        chart_data = []
        for prop in properties:
            if prop.get('analysis_data'):
                analysis = prop['analysis_data']
                property_data = prop['property_data']
                chart_data.append({
                    'Address': property_data.get('formattedAddress', 'Unknown')[:30] + '...',
                    'Monthly Cash Flow': analysis.get('monthly_cash_flow', 0),
                    'Cap Rate': analysis.get('cap_rate', 0),
                    'Cash-on-Cash Return': analysis.get('cash_on_cash_return', 0)
                })
        
        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            
            col1, col2 = st.columns(2)
            
            with col1:
                fig_cash_flow = px.bar(
                    df_chart, 
                    x='Address', 
                    y='Monthly Cash Flow',
                    title='Monthly Cash Flow by Property',
                    color='Monthly Cash Flow',
                    color_continuous_scale='RdYlGn'
                )
                fig_cash_flow.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig_cash_flow, use_container_width=True)
            
            with col2:
                fig_returns = px.scatter(
                    df_chart,
                    x='Cap Rate',
                    y='Cash-on-Cash Return',
                    size='Monthly Cash Flow',
                    hover_name='Address',
                    title='Returns Analysis',
                    color='Monthly Cash Flow',
                    color_continuous_scale='RdYlGn'
                )
                st.plotly_chart(fig_returns, use_container_width=True)
        
        # Recent properties
        st.markdown("### 🏠 Recent Property Analysis")
        
        for i, prop in enumerate(properties[:5]):
            property_data = prop['property_data']
            analysis_data = prop.get('analysis_data', {})
            
            with st.expander(f"📍 {property_data.get('formattedAddress', 'Unknown Address')}"):
                col1, col2, col3, col4 = st.columns(4)
                
                with col1:
                    st.metric("Bedrooms", property_data.get('bedrooms', 'N/A'))
                    st.metric("Bathrooms", property_data.get('bathrooms', 'N/A'))
                
                with col2:
                    st.metric("Square Feet", f"{property_data.get('squareFootage', 0):,}")
                    st.metric("Year Built", property_data.get('yearBuilt', 'N/A'))
                
                with col3:
                    if analysis_data:
                        st.metric("Monthly Cash Flow", f"${analysis_data.get('monthly_cash_flow', 0):,.2f}")
                        st.metric("Cap Rate", f"{analysis_data.get('cap_rate', 0):.2f}%")
                
                with col4:
                    if analysis_data:
                        st.metric("Cash-on-Cash Return", f"{analysis_data.get('cash_on_cash_return', 0):.2f}%")
                        st.metric("Purchase Price", f"${analysis_data.get('purchase_price', 0):,}")
    else:
        st.info("No properties analyzed yet. Start by searching for properties!")

def display_enhanced_property_card(property_data, rent_estimate=None):
    """Display comprehensive property information in enhanced cards"""
    
    # Main property header
    st.markdown(f"""
    <div class="property-card">
        <h2>🏠 {property_data.get('formattedAddress', 'Unknown Address')}</h2>
        <p><strong>Property Type:</strong> {property_data.get('propertyType', 'Unknown')}</p>
        <p><strong>County:</strong> {property_data.get('county', 'Unknown')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Basic property metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{property_data.get('bedrooms', 'N/A')}</h3>
            <p>Bedrooms</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{property_data.get('bathrooms', 'N/A')}</h3>
            <p>Bathrooms</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sqft = property_data.get('squareFootage', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>{sqft:,}</h3>
            <p>Sq Ft</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        year_built = property_data.get('yearBuilt', 'Unknown')
        st.markdown(f"""
        <div class="metric-card">
            <h3>{year_built}</h3>
            <p>Year Built</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Financial Information
    st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
    st.markdown("### 💰 Financial Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        last_sale_price = property_data.get('lastSalePrice', 0)
        if last_sale_price:
            st.metric("Last Sale Price", f"${last_sale_price:,}")
            if sqft and sqft > 0:
                price_per_sqft = last_sale_price / sqft
                st.metric("Price per Sq Ft", f"${price_per_sqft:.2f}")
    
    with col2:
        if rent_estimate and rent_estimate.get('rent'):
            monthly_rent = rent_estimate['rent']
            st.metric("Estimated Monthly Rent", f"${monthly_rent:,}")
            if last_sale_price and last_sale_price > 0:
                annual_rent = monthly_rent * 12
                gross_yield = (annual_rent / last_sale_price) * 100
                st.metric("Gross Rental Yield", f"{gross_yield:.2f}%")
    
    with col3:
        hoa_fee = property_data.get('hoa', {}).get('fee', 0)
        if hoa_fee:
            st.metric("HOA Fee", f"${hoa_fee}/month")
        
        # Latest tax assessment
        tax_assessments = property_data.get('taxAssessments', {})
        if tax_assessments:
            latest_year = max(tax_assessments.keys())
            latest_assessment = tax_assessments[latest_year]['value']
            st.metric(f"{latest_year} Assessment", f"${latest_assessment:,}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Property Features
    features = property_data.get('features', {})
    if features:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 🏡 Property Features")
        
        feature_html = ""
        if features.get('garage'):
            garage_spaces = features.get('garageSpaces', 'Unknown')
            feature_html += f'<span class="feature-badge">🚗 {garage_spaces} Car Garage</span>'
        
        if features.get('pool'):
            pool_type = features.get('poolType', 'Pool')
            feature_html += f'<span class="feature-badge">🏊 {pool_type} Pool</span>'
        
        if features.get('fireplace'):
            fireplace_type = features.get('fireplaceType', 'Fireplace')
            feature_html += f'<span class="feature-badge">🔥 {fireplace_type}</span>'
        
        if features.get('cooling'):
            cooling_type = features.get('coolingType', 'AC')
            feature_html += f'<span class="feature-badge">❄️ {cooling_type}</span>'
        
        if features.get('heating'):
            heating_type = features.get('heatingType', 'Heating')
            feature_html += f'<span class="feature-badge">🔥 {heating_type}</span>'
        
        architecture = features.get('architectureType')
        if architecture:
            feature_html += f'<span class="feature-badge">🏗️ {architecture}</span>'
        
        exterior = features.get('exteriorType')
        if exterior:
            feature_html += f'<span class="feature-badge">🏠 {exterior} Exterior</span>'
        
        roof = features.get('roofType')
        if roof:
            feature_html += f'<span class="feature-badge">🏠 {roof} Roof</span>'
        
        view = features.get('viewType')
        if view:
            feature_html += f'<span class="feature-badge">👁️ {view} View</span>'
        
        st.markdown(feature_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Property Tax History
    property_taxes = property_data.get('propertyTaxes', {})
    if property_taxes:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Property Tax History")
        
        tax_years = sorted(property_taxes.keys(), reverse=True)
        tax_data = []
        for year in tax_years:
            tax_data.append({
                'Year': year,
                'Tax Amount': f"${property_taxes[year]['total']:,}"
            })
        
        df_taxes = pd.DataFrame(tax_data)
        st.dataframe(df_taxes, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Sale History
    history = property_data.get('history', {})
    if history:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Sale History")
        
        history_data = []
        for date_key, event_data in history.items():
            if event_data.get('event') == 'Sale':
                history_data.append({
                    'Date': event_data['date'][:10],
                    'Sale Price': f"${event_data['price']:,}",
                    'Event': event_data['event']
                })
        
        if history_data:
            df_history = pd.DataFrame(history_data)
            st.dataframe(df_history, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Owner Information
    owner = property_data.get('owner', {})
    if owner:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 👤 Owner Information")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Owner Type:** {owner.get('type', 'Unknown')}")
            owner_occupied = property_data.get('ownerOccupied', False)
            st.write(f"**Owner Occupied:** {'Yes' if owner_occupied else 'No'}")
        
        with col2:
            names = owner.get('names', [])
            if names:
                st.write(f"**Owner Names:** {', '.join(names)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def display_market_analysis(property_data, rentcast_api):
    """Display market analysis for the property location"""
    st.markdown("### 📊 Market Analysis")
    
    # Extract city and state from property data
    address_parts = property_data.get('formattedAddress', '').split(', ')
    if len(address_parts) >= 3:
        city = address_parts[-3]
        state = address_parts[-2].split()[0]
        
        market_data = rentcast_api.get_market_data(city, state)
        
        if market_data:
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.metric("Market Rent", f"${market_data.get('averageRent', 0):,}")
            
            with col2:
                st.metric("Price to Rent Ratio", f"{market_data.get('priceToRentRatio', 0):.1f}")
            
            with col3:
                st.metric("Rental Yield", f"{market_data.get('rentalYield', 0):.2f}%")

def display_investment_calculator(property_data, rent_estimate):
    """Display investment calculator with property data"""
    st.markdown("### 🧮 Investment Calculator")
    
    with st.form("investment_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Purchase Details")
            purchase_price = st.number_input(
                "Purchase Price ($)",
                value=property_data.get('lastSalePrice', 200000),
                min_value=0,
                step=1000
            )
            
            down_payment_pct = st.slider("Down Payment (%)", 0, 100, 20, 5)
            interest_rate = st.slider("Interest Rate (%)", 0.0, 15.0, 7.0, 0.25)
            loan_term = st.selectbox("Loan Term (years)", [15, 20, 25, 30], index=3)
        
        with col2:
            st.markdown("#### Income & Expenses")
            monthly_rent = st.number_input(
                "Monthly Rent ($)",
                value=rent_estimate.get('rent', 2000) if rent_estimate else 2000,
                min_value=0,
                step=50
            )
            
            vacancy_rate = st.slider("Vacancy Rate (%)", 0, 20, 5, 1)
            monthly_expenses = st.number_input("Monthly Expenses ($)", value=500, min_value=0, step=50)
        
        calculate = st.form_submit_button("Calculate Returns", type="primary")
        
        if calculate:
            # Calculations
            down_payment = purchase_price * (down_payment_pct / 100)
            loan_amount = purchase_price - down_payment
            
            # Monthly mortgage payment
            monthly_rate = interest_rate / 100 / 12
            num_payments = loan_term * 12
            
            if monthly_rate > 0:
                monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
            else:
                monthly_mortgage = loan_amount / num_payments
            
            effective_rent = monthly_rent * (1 - vacancy_rate / 100)
            total_expenses = monthly_mortgage + monthly_expenses
            monthly_cash_flow = effective_rent - total_expenses
            annual_cash_flow = monthly_cash_flow * 12
            
            # Investment metrics
            cap_rate = (annual_cash_flow + (monthly_mortgage * 12)) / purchase_price * 100
            cash_on_cash_return = annual_cash_flow / down_payment * 100 if down_payment > 0 else 0
            
            # Display results
            col1, col2, col3 = st.columns(3)
            
            with col1:
                color = "green" if monthly_cash_flow > 0 else "red"
                st.markdown(f"""
                <div style="background: {'#4CAF50' if monthly_cash_flow > 0 else '#f44336'}; 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white;">
                    <h3>${monthly_cash_flow:,.2f}</h3>
                    <p>Monthly Cash Flow</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.markdown(f"""
                <div style="background: #2196F3; padding: 1rem; border-radius: 10px; text-align: center; color: white;">
                    <h3>{cap_rate:.2f}%</h3>
                    <p>Cap Rate</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                st.markdown(f"""
                <div style="background: #FF9800; padding: 1rem; border-radius: 10px; text-align: center; color: white;">
                    <h3>{cash_on_cash_return:.2f}%</h3>
                    <p>Cash-on-Cash Return</p>
                </div>
                """, unsafe_allow_html=True)
            
            return {
                "monthly_cash_flow": monthly_cash_flow,
                "cap_rate": cap_rate,
                "cash_on_cash_return": cash_on_cash_return,
                "purchase_price": purchase_price,
                "down_payment": down_payment
            }
    
    return None

def render_investment_calculator_tab(user, supabase_manager):
    """Render investment calculator tab with existing property data"""
    st.markdown('<h1 class="main-header">🧮 Investment Calculator</h1>', unsafe_allow_html=True)
    
    # Get user's saved properties
    saved_properties = supabase_manager.get_user_properties(user.id)
    
    if not saved_properties:
        st.info("No saved properties found. Search for properties first to use the investment calculator.")
        return
    
    # Property selection
    st.markdown("### Select Property for Analysis")
    
    property_options = {}
    for prop in saved_properties:
        prop_data = prop.get('property_data', {})
        address = prop_data.get('formattedAddress', 'Unknown Address')
        property_options[address] = prop
    
    selected_address = st.selectbox(
        "Choose a property:",
        options=list(property_options.keys()),
        help="Select from your previously searched properties"
    )
    
    if selected_address:
        selected_property = property_options[selected_address]
        property_data = selected_property['property_data']
        
        # Display selected property summary
        st.markdown("### 🏠 Selected Property")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Bedrooms", property_data.get('bedrooms', 'N/A'))
        with col2:
            st.metric("Bathrooms", property_data.get('bathrooms', 'N/A'))
        with col3:
            st.metric("Square Feet", f"{property_data.get('squareFootage', 0):,}")
        with col4:
            st.metric("Year Built", property_data.get('yearBuilt', 'N/A'))
        
        # Investment Calculator Form
        st.markdown("### 💰 Investment Parameters")
        
        with st.form("investment_calculator"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Purchase Details")
                purchase_price = st.number_input(
                    "Purchase Price ($)",
                    value=property_data.get('lastSalePrice', 200000),
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
                    value=7.0,
                    step=0.25
                )
                
                loan_term = st.selectbox(
                    "Loan Term (years)",
                    options=[15, 20, 25, 30],
                    index=3
                )
            
            with col2:
                st.markdown("#### Income & Expenses")
                monthly_rent = st.number_input(
                    "Monthly Rent ($)",
                    value=2000,
                    min_value=0,
                    step=50
                )
                
                vacancy_rate = st.slider(
                    "Vacancy Rate (%)",
                    min_value=0,
                    max_value=20,
                    value=5,
                    step=1
                )
                
                # Get property taxes from data
                property_taxes = property_data.get('propertyTaxes', {})
                latest_tax = 0
                if property_taxes:
                    latest_year = max(property_taxes.keys())
                    latest_tax = property_taxes[latest_year]['total']
                
                monthly_property_tax = st.number_input(
                    "Monthly Property Tax ($)",
                    value=latest_tax / 12 if latest_tax else 200,
                    min_value=0,
                    step=10
                )
                
                monthly_insurance = st.number_input(
                    "Monthly Insurance ($)",
                    value=150,
                    min_value=0,
                    step=10
                )
                
                hoa_fee = property_data.get('hoa', {}).get('fee', 0)
                monthly_hoa = st.number_input(
                    "Monthly HOA ($)",
                    value=hoa_fee,
                    min_value=0,
                    step=10
                )
                
                maintenance_pct = st.slider(
                    "Maintenance & Repairs (% of rent)",
                    min_value=0,
                    max_value=20,
                    value=8,
                    step=1
                )
                
                property_mgmt_pct = st.slider(
                    "Property Management (% of rent)",
                    min_value=0,
                    max_value=15,
                    value=10,
                    step=1
                )
            
            calculate_button = st.form_submit_button("🧮 Calculate Investment Metrics", type="primary")
        
        if calculate_button:
            # Calculations
            down_payment = purchase_price * (down_payment_pct / 100)
            loan_amount = purchase_price - down_payment
            
            # Monthly mortgage payment
            monthly_rate = interest_rate / 100 / 12
            num_payments = loan_term * 12
            
            if monthly_rate > 0:
                monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
            else:
                monthly_mortgage = loan_amount / num_payments
            
            # Monthly expenses
            effective_rent = monthly_rent * (1 - vacancy_rate / 100)
            maintenance_cost = monthly_rent * (maintenance_pct / 100)
            mgmt_cost = monthly_rent * (property_mgmt_pct / 100)
            
            total_monthly_expenses = (
                monthly_mortgage + monthly_property_tax + monthly_insurance + 
                monthly_hoa + maintenance_cost + mgmt_cost
            )
            
            monthly_cash_flow = effective_rent - total_monthly_expenses
            annual_cash_flow = monthly_cash_flow * 12
            
            # Investment metrics
            cap_rate = (annual_cash_flow + (monthly_mortgage * 12)) / purchase_price * 100
            cash_on_cash_return = annual_cash_flow / down_payment * 100 if down_payment > 0 else 0
            
            # Display results
            st.markdown("### 📊 Investment Analysis Results")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                color = "green" if monthly_cash_flow > 0 else "red"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #{'4CAF50' if monthly_cash_flow > 0 else 'f44336'} 0%, #{'66BB6A' if monthly_cash_flow > 0 else 'ef5350'} 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>${monthly_cash_flow:,.2f}</h3>
                    <p>Monthly Cash Flow</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                color = "green" if cap_rate > 6 else "orange" if cap_rate > 4 else "red"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #{'4CAF50' if cap_rate > 6 else 'FF9800' if cap_rate > 4 else 'f44336'} 0%, 
                           #{'66BB6A' if cap_rate > 6 else 'FFB74D' if cap_rate > 4 else 'ef5350'} 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>{cap_rate:.2f}%</h3>
                    <p>Cap Rate</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                color = "green" if cash_on_cash_return > 8 else "orange" if cash_on_cash_return > 5 else "red"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #{'4CAF50' if cash_on_cash_return > 8 else 'FF9800' if cash_on_cash_return > 5 else 'f44336'} 0%, 
                           #{'66BB6A' if cash_on_cash_return > 8 else 'FFB74D' if cash_on_cash_return > 5 else 'ef5350'} 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>{cash_on_cash_return:.2f}%</h3>
                    <p>Cash-on-Cash Return</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #2196F3 0%, #42A5F5 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>${down_payment:,.0f}</h3>
                    <p>Initial Investment</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Detailed breakdown
            st.markdown("### 💰 Financial Breakdown")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Monthly Income")
                st.write(f"Gross Rent: ${monthly_rent:,.2f}")
                st.write(f"Vacancy Loss ({vacancy_rate}%): -${monthly_rent * vacancy_rate / 100:,.2f}")
                st.write(f"**Effective Income: ${effective_rent:,.2f}**")
            
            with col2:
                st.markdown("#### Monthly Expenses")
                st.write(f"Mortgage Payment: ${monthly_mortgage:,.2f}")
                st.write(f"Property Tax: ${monthly_property_tax:,.2f}")
                st.write(f"Insurance: ${monthly_insurance:,.2f}")
                st.write(f"HOA: ${monthly_hoa:,.2f}")
                st.write(f"Maintenance ({maintenance_pct}%): ${maintenance_cost:,.2f}")
                st.write(f"Property Mgmt ({property_mgmt_pct}%): ${mgmt_cost:,.2f}")
                st.write(f"**Total Expenses: ${total_monthly_expenses:,.2f}**")
            
            # Investment recommendation
            st.markdown("### 🎯 Investment Recommendation")
            
            if monthly_cash_flow > 200 and cap_rate > 6 and cash_on_cash_return > 8:
                recommendation = "🟢 **EXCELLENT INVESTMENT** - Strong cash flow and returns across all metrics."
            elif monthly_cash_flow > 0 and cap_rate > 4 and cash_on_cash_return > 5:
                recommendation = "🟡 **GOOD INVESTMENT** - Positive returns with moderate performance."
            elif monthly_cash_flow > -100 and cap_rate > 2:
                recommendation = "🟠 **MARGINAL INVESTMENT** - Consider negotiating price or improving rent."
            else:
                recommendation = "🔴 **POOR INVESTMENT** - Negative cash flow and low returns. Avoid or restructure."
            
            st.markdown(recommendation)
            
            # Save analysis
            analysis_data = {
                "monthly_cash_flow": monthly_cash_flow,
                "cap_rate": cap_rate,
                "cash_on_cash_return": cash_on_cash_return,
                "purchase_price": purchase_price,
                "down_payment": down_payment,
                "monthly_rent": monthly_rent,
                "total_monthly_expenses": total_monthly_expenses,
                "recommendation": recommendation
            }
            
            # Update property with new analysis
            supabase_manager.update_property_analysis(selected_property['id'], analysis_data)
            st.success("Investment analysis saved to your dashboard!")

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
        st.info("""
        **Setup Instructions:**
        Add the following to your Streamlit secrets:
        
        ```toml
        RENTCAST_API_KEY = "your_rentcast_api_key"
        SUPABASE_URL = "your_supabase_url"
        SUPABASE_KEY = "your_supabase_anon_key"
        
def display_enhanced_property_card(property_data, rent_estimate=None):
    """Display comprehensive property information in enhanced cards"""
    
    st.markdown("""
    <style>
    .property-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .property-detail-card {
        background: white;
        padding: 1.5rem;
        border-radius: 10px;
        margin: 1rem 0;
        box-shadow: 0 4px 15px rgba(0,0,0,0.1);
        border-left: 4px solid #667eea;
    }
    .metric-card {
        background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
        padding: 1rem;
        border-radius: 10px;
        text-align: center;
        color: white;
        margin: 0.5rem 0;
    }
    .feature-badge {
        background: #4CAF50;
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-size: 0.8rem;
        margin: 0.2rem;
        display: inline-block;
    }
    </style>
    """, unsafe_allow_html=True)
    
    # Main property header
    st.markdown(f"""
    <div class="property-card">
        <h2>🏠 {property_data.get('formattedAddress', 'Unknown Address')}</h2>
        <p><strong>Property Type:</strong> {property_data.get('propertyType', 'Unknown')}</p>
        <p><strong>County:</strong> {property_data.get('county', 'Unknown')}</p>
    </div>
    """, unsafe_allow_html=True)
    
    # Basic property metrics
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{property_data.get('bedrooms', 'N/A')}</h3>
            <p>Bedrooms</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"""
        <div class="metric-card">
            <h3>{property_data.get('bathrooms', 'N/A')}</h3>
            <p>Bathrooms</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        sqft = property_data.get('squareFootage', 0)
        st.markdown(f"""
        <div class="metric-card">
            <h3>{sqft:,}</h3>
            <p>Sq Ft</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        year_built = property_data.get('yearBuilt', 'Unknown')
        st.markdown(f"""
        <div class="metric-card">
            <h3>{year_built}</h3>
            <p>Year Built</p>
        </div>
        """, unsafe_allow_html=True)
    
    # Financial Information
    st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
    st.markdown("### 💰 Financial Information")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        last_sale_price = property_data.get('lastSalePrice', 0)
        if last_sale_price:
            st.metric("Last Sale Price", f"${last_sale_price:,}")
            if sqft and sqft > 0:
                price_per_sqft = last_sale_price / sqft
                st.metric("Price per Sq Ft", f"${price_per_sqft:.2f}")
    
    with col2:
        if rent_estimate and rent_estimate.get('rent'):
            monthly_rent = rent_estimate['rent']
            st.metric("Estimated Monthly Rent", f"${monthly_rent:,}")
            if last_sale_price and last_sale_price > 0:
                annual_rent = monthly_rent * 12
                gross_yield = (annual_rent / last_sale_price) * 100
                st.metric("Gross Rental Yield", f"{gross_yield:.2f}%")
    
    with col3:
        hoa_fee = property_data.get('hoa', {}).get('fee', 0)
        if hoa_fee:
            st.metric("HOA Fee", f"${hoa_fee}/month")
        
        # Latest tax assessment
        tax_assessments = property_data.get('taxAssessments', {})
        if tax_assessments:
            latest_year = max(tax_assessments.keys())
            latest_assessment = tax_assessments[latest_year]['value']
            st.metric(f"{latest_year} Assessment", f"${latest_assessment:,}")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Property Features
    features = property_data.get('features', {})
    if features:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 🏡 Property Features")
        
        feature_html = ""
        if features.get('garage'):
            garage_spaces = features.get('garageSpaces', 'Unknown')
            feature_html += f'<span class="feature-badge">🚗 {garage_spaces} Car Garage</span>'
        
        if features.get('pool'):
            pool_type = features.get('poolType', 'Pool')
            feature_html += f'<span class="feature-badge">🏊 {pool_type} Pool</span>'
        
        if features.get('fireplace'):
            fireplace_type = features.get('fireplaceType', 'Fireplace')
            feature_html += f'<span class="feature-badge">🔥 {fireplace_type}</span>'
        
        if features.get('cooling'):
            cooling_type = features.get('coolingType', 'AC')
            feature_html += f'<span class="feature-badge">❄️ {cooling_type}</span>'
        
        if features.get('heating'):
            heating_type = features.get('heatingType', 'Heating')
            feature_html += f'<span class="feature-badge">🔥 {heating_type}</span>'
        
        architecture = features.get('architectureType')
        if architecture:
            feature_html += f'<span class="feature-badge">🏗️ {architecture}</span>'
        
        exterior = features.get('exteriorType')
        if exterior:
            feature_html += f'<span class="feature-badge">🏠 {exterior} Exterior</span>'
        
        roof = features.get('roofType')
        if roof:
            feature_html += f'<span class="feature-badge">🏠 {roof} Roof</span>'
        
        view = features.get('viewType')
        if view:
            feature_html += f'<span class="feature-badge">👁️ {view} View</span>'
        
        st.markdown(feature_html, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Property Tax History
    property_taxes = property_data.get('propertyTaxes', {})
    if property_taxes:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 📊 Property Tax History")
        
        tax_years = sorted(property_taxes.keys(), reverse=True)
        tax_data = []
        for year in tax_years:
            tax_data.append({
                'Year': year,
                'Tax Amount': f"${property_taxes[year]['total']:,}"
            })
        
        df_taxes = pd.DataFrame(tax_data)
        st.dataframe(df_taxes, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Sale History
    history = property_data.get('history', {})
    if history:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 📈 Sale History")
        
        history_data = []
        for date_key, event_data in history.items():
            if event_data.get('event') == 'Sale':
                history_data.append({
                    'Date': event_data['date'][:10],  # Format date
                    'Sale Price': f"${event_data['price']:,}",
                    'Event': event_data['event']
                })
        
        if history_data:
            df_history = pd.DataFrame(history_data)
            st.dataframe(df_history, use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Owner Information
    owner = property_data.get('owner', {})
    if owner:
        st.markdown('<div class="property-detail-card">', unsafe_allow_html=True)
        st.markdown("### 👤 Owner Information")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Owner Type:** {owner.get('type', 'Unknown')}")
            owner_occupied = property_data.get('ownerOccupied', False)
            st.write(f"**Owner Occupied:** {'Yes' if owner_occupied else 'No'}")
        
        with col2:
            names = owner.get('names', [])
            if names:
                st.write(f"**Owner Names:** {', '.join(names)}")
        
        st.markdown('</div>', unsafe_allow_html=True)

def render_investment_calculator_tab(user, supabase_manager):
    """Render investment calculator tab with existing property data"""
    st.markdown('<h1 class="main-header">🧮 Investment Calculator</h1>', unsafe_allow_html=True)
    
    # Get user's saved properties
    saved_properties = supabase_manager.get_user_properties(user.id)
    
    if not saved_properties:
        st.info("No saved properties found. Search for properties first to use the investment calculator.")
        return
    
    # Property selection
    st.markdown("### Select Property for Analysis")
    
    property_options = {}
    for prop in saved_properties:
        prop_data = prop.get('property_data', {})
        address = prop_data.get('formattedAddress', 'Unknown Address')
        property_options[address] = prop
    
    selected_address = st.selectbox(
        "Choose a property:",
        options=list(property_options.keys()),
        help="Select from your previously searched properties"
    )
    
    if selected_address:
        selected_property = property_options[selected_address]
        property_data = selected_property['property_data']
        
        # Display selected property summary
        st.markdown("### 🏠 Selected Property")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Bedrooms", property_data.get('bedrooms', 'N/A'))
        with col2:
            st.metric("Bathrooms", property_data.get('bathrooms', 'N/A'))
        with col3:
            st.metric("Square Feet", f"{property_data.get('squareFootage', 0):,}")
        with col4:
            st.metric("Year Built", property_data.get('yearBuilt', 'N/A'))
        
        # Investment Calculator Form
        st.markdown("### 💰 Investment Parameters")
        
        with st.form("investment_calculator"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Purchase Details")
                purchase_price = st.number_input(
                    "Purchase Price ($)",
                    value=property_data.get('lastSalePrice', 200000),
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
                    value=7.0,
                    step=0.25
                )
                
                loan_term = st.selectbox(
                    "Loan Term (years)",
                    options=[15, 20, 25, 30],
                    index=3
                )
            
            with col2:
                st.markdown("#### Income & Expenses")
                monthly_rent = st.number_input(
                    "Monthly Rent ($)",
                    value=2000,
                    min_value=0,
                    step=50
                )
                
                vacancy_rate = st.slider(
                    "Vacancy Rate (%)",
                    min_value=0,
                    max_value=20,
                    value=5,
                    step=1
                )
                
                # Get property taxes from data
                property_taxes = property_data.get('propertyTaxes', {})
                latest_tax = 0
                if property_taxes:
                    latest_year = max(property_taxes.keys())
                    latest_tax = property_taxes[latest_year]['total']
                
                monthly_property_tax = st.number_input(
                    "Monthly Property Tax ($)",
                    value=latest_tax / 12 if latest_tax else 200,
                    min_value=0,
                    step=10
                )
                
                monthly_insurance = st.number_input(
                    "Monthly Insurance ($)",
                    value=150,
                    min_value=0,
                    step=10
                )
                
                hoa_fee = property_data.get('hoa', {}).get('fee', 0)
                monthly_hoa = st.number_input(
                    "Monthly HOA ($)",
                    value=hoa_fee,
                    min_value=0,
                    step=10
                )
                
                maintenance_pct = st.slider(
                    "Maintenance & Repairs (% of rent)",
                    min_value=0,
                    max_value=20,
                    value=8,
                    step=1
                )
                
                property_mgmt_pct = st.slider(
                    "Property Management (% of rent)",
                    min_value=0,
                    max_value=15,
                    value=10,
                    step=1
                )
            
            calculate_button = st.form_submit_button("🧮 Calculate Investment Metrics", type="primary")
        
        if calculate_button:
            # Calculations
            down_payment = purchase_price * (down_payment_pct / 100)
            loan_amount = purchase_price - down_payment
            
            # Monthly mortgage payment
            monthly_rate = interest_rate / 100 / 12
            num_payments = loan_term * 12
            
            if monthly_rate > 0:
                monthly_mortgage = loan_amount * (monthly_rate * (1 + monthly_rate)**num_payments) / ((1 + monthly_rate)**num_payments - 1)
            else:
                monthly_mortgage = loan_amount / num_payments
            
            # Monthly expenses
            effective_rent = monthly_rent * (1 - vacancy_rate / 100)
            maintenance_cost = monthly_rent * (maintenance_pct / 100)
            mgmt_cost = monthly_rent * (property_mgmt_pct / 100)
            
            total_monthly_expenses = (
                monthly_mortgage + monthly_property_tax + monthly_insurance + 
                monthly_hoa + maintenance_cost + mgmt_cost
            )
            
            monthly_cash_flow = effective_rent - total_monthly_expenses
            annual_cash_flow = monthly_cash_flow * 12
            
            # Investment metrics
            cap_rate = (annual_cash_flow + (monthly_mortgage * 12)) / purchase_price * 100
            cash_on_cash_return = annual_cash_flow / down_payment * 100 if down_payment > 0 else 0
            
            # Total ROI (simplified)
            total_roi = cash_on_cash_return
            
            # Display results
            st.markdown("### 📊 Investment Analysis Results")
            
            # Key metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                color = "green" if monthly_cash_flow > 0 else "red"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #{'4CAF50' if monthly_cash_flow > 0 else 'f44336'} 0%, #{'66BB6A' if monthly_cash_flow > 0 else 'ef5350'} 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>${monthly_cash_flow:,.2f}</h3>
                    <p>Monthly Cash Flow</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                color = "green" if cap_rate > 6 else "orange" if cap_rate > 4 else "red"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #{'4CAF50' if cap_rate > 6 else 'FF9800' if cap_rate > 4 else 'f44336'} 0%, 
                           #{'66BB6A' if cap_rate > 6 else 'FFB74D' if cap_rate > 4 else 'ef5350'} 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>{cap_rate:.2f}%</h3>
                    <p>Cap Rate</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col3:
                color = "green" if cash_on_cash_return > 8 else "orange" if cash_on_cash_return > 5 else "red"
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #{'4CAF50' if cash_on_cash_return > 8 else 'FF9800' if cash_on_cash_return > 5 else 'f44336'} 0%, 
                           #{'66BB6A' if cash_on_cash_return > 8 else 'FFB74D' if cash_on_cash_return > 5 else 'ef5350'} 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>{cash_on_cash_return:.2f}%</h3>
                    <p>Cash-on-Cash Return</p>
                </div>
                """, unsafe_allow_html=True)
            
            with col4:
                st.markdown(f"""
                <div style="background: linear-gradient(135deg, #2196F3 0%, #42A5F5 100%); 
                           padding: 1rem; border-radius: 10px; text-align: center; color: white; margin: 0.5rem 0;">
                    <h3>${down_payment:,.0f}</h3>
                    <p>Initial Investment</p>
                </div>
                """, unsafe_allow_html=True)
            
            # Detailed breakdown
            st.markdown("### 💰 Financial Breakdown")
            
            col1, col2 = st.columns(2)
            
            with col1:
                st.markdown("#### Monthly Income")
                st.write(f"Gross Rent: ${monthly_rent:,.2f}")
                st.write(f"Vacancy Loss ({vacancy_rate}%): -${monthly_rent * vacancy_rate / 100:,.2f}")
                st.write(f"**Effective Income: ${effective_rent:,.2f}**")
            
            with col2:
                st.markdown("#### Monthly Expenses")
                st.write(f"Mortgage Payment: ${monthly_mortgage:,.2f}")
                st.write(f"Property Tax: ${monthly_property_tax:,.2f}")
                st.write(f"Insurance: ${monthly_insurance:,.2f}")
                st.write(f"HOA: ${monthly_hoa:,.2f}")
                st.write(f"Maintenance ({maintenance_pct}%): ${maintenance_cost:,.2f}")
                st.write(f"Property Mgmt ({property_mgmt_pct}%): ${mgmt_cost:,.2f}")
                st.write(f"**Total Expenses: ${total_monthly_expenses:,.2f}**")
            
            # Investment recommendation
            st.markdown("### 🎯 Investment Recommendation")
            
            if monthly_cash_flow > 200 and cap_rate > 6 and cash_on_cash_return > 8:
                recommendation = "🟢 **EXCELLENT INVESTMENT** - Strong cash flow and returns across all metrics."
            elif monthly_cash_flow > 0 and cap_rate > 4 and cash_on_cash_return > 5:
                recommendation = "🟡 **GOOD INVESTMENT** - Positive returns with moderate performance."
            elif monthly_cash_flow > -100 and cap_rate > 2:
                recommendation = "🟠 **MARGINAL INVESTMENT** - Consider negotiating price or improving rent."
            else:
                recommendation = "🔴 **POOR INVESTMENT** - Negative cash flow and low returns. Avoid or restructure."
            
            st.markdown(recommendation)
            
            # Save analysis
            analysis_data = {
                "monthly_cash_flow": monthly_cash_flow,
                "cap_rate": cap_rate,
                "cash_on_cash_return": cash_on_cash_return,
                "purchase_price": purchase_price,
                "down_payment": down_payment,
                "monthly_rent": monthly_rent,
                "total_monthly_expenses": total_monthly_expenses,
                "recommendation": recommendation
            }
            
            # Update property with new analysis
            supabase_manager.update_property_analysis(selected_property['id'], analysis_data)
            st.success("Investment analysis saved to your dashboard!")

# ... existing code ...

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
        st.info("""
        **Setup Instructions:**
        Add the following to your Streamlit secrets:
        
        ```toml
        RENTCAST_API_KEY = "your_rentcast_api_key"
        SUPABASE_URL = "your_supabase_url"
        SUPABASE_KEY = "your_supabase_anon_key"
        ```
        """)
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
        
        # <CHANGE> Added investment calculator tab
        if st.button("🧮 Investment Calculator", use_container_width=True):
            st.session_state.current_page = "calculator"
        
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
                
                # <CHANGE> Use enhanced property card display
                display_enhanced_property_card(property_data, rent_estimate)
                
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
    
    # <CHANGE> Added investment calculator tab functionality
    elif st.session_state.current_page == "calculator":
        render_investment_calculator_tab(user, supabase_manager)

if __name__ == "__main__":
    main()
[V0_FILE]plaintext:file=".streamlit/secrets.toml" isMerged="true"
# Streamlit Secrets Configuration
# Place this file in .streamlit/secrets.toml in your project root

[supabase]
url = "your_supabase_project_url_here"
key = "your_supabase_anon_key_here"

[rentcast]
api_key = "your_rentcast_api_key_here"

# Optional: Database connection string if using direct database access
# [connections.postgresql]
# dialect = "postgresql"
# host = "your_host"
# port = "5432"
# database = "your_database"
# username = "your_username"
# password = "your_password"
