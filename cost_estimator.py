import streamlit as st
import math

# --- Pricing & Core Logic Constants ---
# Based on public pricing as of mid-2024.
PRICE_PER_VIDEO_MINUTE_TRANSCODE = 0.0075  # AWS MediaConvert (Basic Tier, SD/HD)
PRICE_PER_1000_CHARS_AI = 0.09             # ElevenLabs (Scale Plan)
PRICE_PER_GB_STORAGE = 0.015               # Cloudflare R2
PRICE_PER_MILLION_READ_OPS = 0.36          # Cloudflare R2 (Class B Operations)
AD_IMPRESSION_THRESHOLD = 2000000          # AdSense for Video eligibility

# --- Calculation Functions ---
def calculate_financials(
    mau, dau_percent, upload_percent, video_length_sec,
    sub_price, sub_percent, ad_rpm, data_consumption_gb
):
    """Calculates all cost, revenue, and profit components."""

    # --- 1. Cost Calculation ---
    costs = {}
    if mau == 0:
        costs = {key: 0 for key in ["media_processing", "storage_delivery", "database", "compute_recommendation", "devops", "total"]}
    else:
        # User & Content Metrics for costs
        dau = mau * (dau_percent / 100.0)
        videos_per_month = dau * (upload_percent / 100.0) * 30
        chars_per_video = (video_length_sec / 30.0) * 450
        num_renditions = 5

        transcode_cost = videos_per_month * (video_length_sec / 60.0) * num_renditions * PRICE_PER_VIDEO_MINUTE_TRANSCODE
        ai_cost = (videos_per_month * (chars_per_video * 2) / 1000) * PRICE_PER_1000_CHARS_AI
        costs["media_processing"] = transcode_cost + ai_cost

        total_videos_stored = videos_per_month * 12
        total_gb_stored = (total_videos_stored * 75) / 1024
        storage_cost = total_gb_stored * PRICE_PER_GB_STORAGE
        
        # Estimate read operations based on total data delivered
        total_gb_delivered = mau * data_consumption_gb
        read_ops_millions = total_gb_delivered / 10 # Rough guess: 1M ops per 10TB
        read_ops_cost = read_ops_millions * PRICE_PER_MILLION_READ_OPS
        costs["storage_delivery"] = storage_cost + read_ops_cost

        scale_factor = math.log10(mau + 1) / math.log10(100000)
        costs["database"] = 2550 * scale_factor**1.5
        costs["compute_recommendation"] = 3250 * scale_factor**1.8
        costs["devops"] = 50 * scale_factor
        costs["total"] = sum(costs.values())

    # --- 2. Revenue Calculation ---
    # Subscription Revenue
    num_subscribers = mau * (sub_percent / 100.0)
    subscription_revenue = num_subscribers * sub_price

    # Ad Revenue
    # Estimate views based on data consumption. Assume 15MB for a 30s video.
    mb_per_video = (video_length_sec / 30.0) * 15
    gb_per_video = mb_per_video / 1024
    views_per_user = data_consumption_gb / gb_per_video if gb_per_video > 0 else 0
    total_monthly_impressions = mau * views_per_user
    
    ad_revenue = 0
    ad_eligibility_message = ""
    if total_monthly_impressions >= AD_IMPRESSION_THRESHOLD:
        ad_revenue = (total_monthly_impressions / 1000) * ad_rpm
        ad_eligibility_message = "✅ Platform is eligible for AdSense for Video."
    else:
        ad_eligibility_message = f"⚠️ Platform is NOT eligible for AdSense. Needs >{AD_IMPRESSION_THRESHOLD:,.0f} monthly views."

    total_revenue = subscription_revenue + ad_revenue

    # --- 3. Net Profit Calculation ---
    net_profit = total_revenue - costs["total"]

    return {
        "costs": costs,
        "subscription_revenue": subscription_revenue,
        "ad_revenue": ad_revenue,
        "total_revenue": total_revenue,
        "net_profit": net_profit,
        "ad_eligibility_message": ad_eligibility_message,
    }

# --- Streamlit App UI ---
st.set_page_config(layout="wide", page_title="App Profitability Estimator")

st.title("📈 Language Learning App Profitability Estimator")
st.markdown("Adjust the sliders to model costs, revenue, and net profit based on key business metrics.")

# --- Sidebar for Hyperparameters ---
with st.sidebar:
    st.header("⚙️ Core Assumptions")

    with st.expander("User Base & Activity", expanded=True):
        mau = st.slider("Monthly Active Users (MAU)", 0, 20000000, 1000000, 100000, format="%d")
        dau_percent = st.slider("Daily Active Users (% of MAU)", 5, 50, 20, 1)
        # CHANGED: Max value increased to 20 GB
        data_consumption_gb = st.slider("Monthly Data Consumption per User (GB)", 0.1, 20.0, 0.7, 0.1)

    with st.expander("Content & Uploads", expanded=True):
        upload_percent = st.slider("Content Uploads (% of DAU per day)", 1, 20, 5, 1)
        # CHANGED: Min value is now 5 and default is 30
        video_length_sec = st.slider("Average Video Length (seconds)", 5, 120, 30, 5)

    st.header("💰 Monetization Levers")
    with st.expander("Subscription Model", expanded=True):
        sub_price = st.slider("Monthly Subscription Price ($)", 0.0, 30.0, 7.99, 0.50)
        sub_percent = st.slider("% of MAUs that Subscribe", 0.25, 40.0, 2.0, 0.25, format="%.2f%%")

    with st.expander("Advertising Model", expanded=True):
        ad_rpm = st.slider("Ad RPM (per 1,000 views)", 0.04, 0.25, 0.10, 0.01, format="$%.2f")

# --- Main Panel for Results ---
financials = calculate_financials(
    mau, dau_percent, upload_percent, video_length_sec,
    sub_price, sub_percent, ad_rpm, data_consumption_gb
)

st.header("Financial Summary")

profit_color = "normal"
if financials['net_profit'] > 0:
    profit_color = "inverse"
elif financials['net_profit'] < 0:
    profit_color = "off"

st.metric(
    label="Net Monthly Profit (Revenue - Costs)",
    value=f"${financials['net_profit']:,.0f}",
    delta_color=profit_color,
    help="Positive numbers indicate profit; negative numbers indicate loss."
)
st.markdown("---")

# --- Revenue vs Costs Breakdown ---
col1, col2 = st.columns(2)

with col1:
    st.subheader("Revenue Breakdown")
    st.metric(label="Total Monthly Revenue", value=f"${financials['total_revenue']:,.0f}")
    st.metric(label="↳ Subscription Revenue", value=f"${financials['subscription_revenue']:,.0f}")
    st.metric(label="↳ Ad Revenue", value=f"${financials['ad_revenue']:,.0f}")
    st.info(financials['ad_eligibility_message'])

with col2:
    st.subheader("Cost Breakdown")
    st.metric(label="Total Monthly Costs", value=f"${financials['costs']['total']:,.0f}")
    st.metric(label="↳ Media Processing & AI", value=f"${financials['costs']['media_processing']:,.0f}")
    st.metric(label="↳ Storage & Delivery", value=f"${financials['costs']['storage_delivery']:,.0f}")
    st.metric(label="↳ Database & Compute", value=f"${financials['costs']['database'] + financials['costs']['compute_recommendation']:,.0f}")

st.markdown("---")

# --- Pricing Information Expander ---
with st.expander("View Pricing Information & Sources"):
    st.markdown(f"""
    ### 🤖 Media Processing & AI
    - **AWS Elemental MediaConvert:** `${PRICE_PER_VIDEO_MINUTE_TRANSCODE}` per minute. [Source](https://aws.amazon.com/elemental-mediaconvert/pricing/)
    - **ElevenLabs API:** `${PRICE_PER_1000_CHARS_AI}` per 1,000 characters. [Source](https://elevenlabs.io/pricing)

    ### 💽 Storage & Delivery
    - **Cloudflare R2 Storage:** `${PRICE_PER_GB_STORAGE}` per GB-month. [Source](https://developers.cloudflare.com/r2/pricing/)
    - **Cloudflare CDN Delivery:** $0 egress fee. [Source](https://www.cloudflare.com/bandwidth-alliance/)

    ### 💸 Advertising
    - **AdSense for Video RPM:** Based on the provided report indicating a range of $0.04 - $0.20 for short-form video.
    - **Eligibility:** Requires >2M monthly video impressions. [Source](https://support.google.com/adsense/answer/9917300)

    ### 🗄️ Database, 💻 Compute, & 🛠️ DevOps
    Costs for these services are estimated using a non-linear scaling model. For detailed pricing, see the official sources on their respective websites (AWS, ScyllaDB, Pinecone, etc.).
    """)