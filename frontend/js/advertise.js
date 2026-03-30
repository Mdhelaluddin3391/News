const ADVERTISE_PAGE_API_URL = `${CONFIG.API_BASE_URL}/advertise-page/`;
const AD_INQUIRY_API_URL = `${CONFIG.API_BASE_URL}/contact/`;

const DEFAULT_ADVERTISE_PAGE = {
    hero_title: "Grow Your Brand With Forex Times",
    hero_description: "Reach a highly engaged audience through our premium digital news platform. We offer strategic ad placements to maximize your visibility.",
    slots_section_title: "Available Ad Slots",
    inquiry_title: "Advertisement Inquiry",
    inquiry_description: "Fill out the form below and our advertising team will get back to you with pricing and analytics details.",
    submit_button_text: "Submit Inquiry",
    success_message: "Thank you for your interest! Our advertising team will contact you shortly.",
    options: [
        {
            title: "Header Banner",
            description: "Premium visibility at the very top of our website. Appears on all pages. Highly recommended for maximum reach.",
            icon_class: "fas fa-rectangle-ad",
            inquiry_value: "Header Banner",
            show_on_page: true,
            show_in_inquiry_form: true
        },
        {
            title: "Sidebar Top",
            description: "Sticky advertisement on the right sidebar. Stays visible as users scroll through breaking news and articles.",
            icon_class: "fas fa-border-all",
            inquiry_value: "Sidebar Ad",
            show_on_page: true,
            show_in_inquiry_form: true
        },
        {
            title: "In-Article Ad",
            description: "Placed directly inside our news articles. Great for capturing the attention of highly engaged readers.",
            icon_class: "fas fa-newspaper",
            inquiry_value: "In-Article Ad",
            show_on_page: true,
            show_in_inquiry_form: true
        },
        {
            title: "Brand Collaboration",
            description: "Sponsored posts, brand campaigns, and custom integrations tailored to your launch timeline and audience goals.",
            icon_class: "fas fa-handshake",
            inquiry_value: "Brand Collaboration / Sponsored Post",
            show_on_page: false,
            show_in_inquiry_form: true
        },
        {
            title: "Consultation",
            description: "Need help selecting a package? Our team can suggest the right placement mix.",
            icon_class: "fas fa-comments",
            inquiry_value: "Not sure yet, need consultation",
            show_on_page: false,
            show_in_inquiry_form: true
        }
    ]
};

let advertisePageConfig = { ...DEFAULT_ADVERTISE_PAGE };

function mergeAdvertiseConfig(payload = {}) {
    return {
        ...DEFAULT_ADVERTISE_PAGE,
        ...payload,
        options: Array.isArray(payload.options) && payload.options.length > 0
            ? payload.options
            : DEFAULT_ADVERTISE_PAGE.options
    };
}

function renderAdvertiseOptions(options = []) {
    const slotsGrid = document.getElementById("advertise-slots-grid");
    const slotSelect = document.getElementById("interested-slot");
    if (!slotsGrid || !slotSelect) {
        return;
    }

    const pageOptions = options.filter((option) => option.show_on_page !== false);
    const inquiryOptions = options.filter((option) => option.show_in_inquiry_form !== false);

    slotsGrid.innerHTML = "";
    if (pageOptions.length === 0) {
        const emptyState = document.createElement("p");
        emptyState.style.textAlign = "center";
        emptyState.style.gridColumn = "1 / -1";
        emptyState.style.color = "var(--gray)";
        emptyState.textContent = "Advertising options will be published here soon.";
        slotsGrid.appendChild(emptyState);
    } else {
        pageOptions.forEach((option) => {
            const card = document.createElement("div");
            card.className = "ad-slot-card";

            const icon = document.createElement("i");
            icon.className = option.icon_class || "fas fa-bullhorn";

            const heading = document.createElement("h3");
            heading.textContent = option.title || option.inquiry_value || "Advertising Slot";

            const description = document.createElement("p");
            description.style.color = "var(--gray)";
            description.style.fontSize = "0.95rem";
            description.style.marginTop = "10px";
            description.textContent = option.description || "";

            card.appendChild(icon);
            card.appendChild(heading);
            card.appendChild(description);
            slotsGrid.appendChild(card);
        });
    }

    slotSelect.innerHTML = "";
    const placeholderOption = document.createElement("option");
    placeholderOption.value = "";
    placeholderOption.textContent = "-- Select an option --";
    slotSelect.appendChild(placeholderOption);

    inquiryOptions.forEach((option) => {
        const selectOption = document.createElement("option");
        selectOption.value = option.inquiry_value || option.title || "";
        selectOption.textContent = option.inquiry_value || option.title || "Advertising Option";
        slotSelect.appendChild(selectOption);
    });
}

function renderAdvertisePage(config) {
    const heroTitle = document.getElementById("advertise-hero-title");
    const heroDescription = document.getElementById("advertise-hero-description");
    const slotsTitle = document.getElementById("advertise-slots-title");
    const inquiryTitle = document.getElementById("advertise-inquiry-title");
    const inquiryDescription = document.getElementById("advertise-inquiry-description");
    const submitButton = document.getElementById("advertise-submit-btn");

    if (heroTitle) heroTitle.textContent = config.hero_title;
    if (heroDescription) heroDescription.textContent = config.hero_description;
    if (slotsTitle) slotsTitle.textContent = config.slots_section_title;
    if (inquiryTitle) inquiryTitle.textContent = config.inquiry_title;
    if (inquiryDescription) inquiryDescription.textContent = config.inquiry_description;
    if (submitButton) submitButton.textContent = config.submit_button_text;

    renderAdvertiseOptions(config.options);
}

async function loadAdvertisePageConfig() {
    try {
        const response = await fetch(ADVERTISE_PAGE_API_URL);
        if (!response.ok) {
            throw new Error(`Failed to load advertise page config (${response.status})`);
        }

        const payload = await response.json();
        advertisePageConfig = mergeAdvertiseConfig(payload);
        renderAdvertisePage(advertisePageConfig);
    } catch (error) {
        console.error("Advertise page config error:", error);
        advertisePageConfig = mergeAdvertiseConfig();
        renderAdvertisePage(advertisePageConfig);
    }
}

function setupAdvertiseForm() {
    const form = document.getElementById("advertise-form");
    if (!form) return;

    form.addEventListener("submit", async function (e) {
        e.preventDefault();

        const companyName = document.getElementById("company-name").value.trim();
        const email = document.getElementById("email").value.trim();
        const interestedSlot = document.getElementById("interested-slot").value;
        const userMessage = document.getElementById("message").value.trim();
        const submitBtn = this.querySelector(".submit-btn");
        const statusDiv = document.getElementById("ad-status");

        const subject = `Ad Inquiry: ${interestedSlot} - ${companyName}`;
        const finalMessage = `Company: ${companyName}\nInterested Slot: ${interestedSlot}\n\nMessage:\n${userMessage}`;

        statusDiv.style.display = "none";
        submitBtn.disabled = true;
        submitBtn.textContent = "Submitting...";

        try {
            const response = await fetch(AD_INQUIRY_API_URL, {
                method: "POST",
                headers: {
                    "Content-Type": "application/json",
                },
                body: JSON.stringify({
                    name: companyName,
                    email: email,
                    subject: subject,
                    message: finalMessage
                })
            });

            if (response.ok) {
                statusDiv.textContent = advertisePageConfig.success_message || DEFAULT_ADVERTISE_PAGE.success_message;
                statusDiv.style.backgroundColor = "#d1fae5";
                statusDiv.style.color = "#065f46";
                statusDiv.style.border = "1px solid #a7f3d0";
                statusDiv.style.display = "block";
                this.reset();
            } else {
                const data = await response.json();
                throw new Error(data.detail || "Failed to submit inquiry.");
            }
        } catch (error) {
            console.error("Ad inquiry form error:", error);
            statusDiv.textContent = error.message || "An error occurred while submitting. Please try again later.";
            statusDiv.style.backgroundColor = "#fee2e2";
            statusDiv.style.color = "#b91c1c";
            statusDiv.style.border = "1px solid #fecaca";
            statusDiv.style.display = "block";
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = advertisePageConfig.submit_button_text || DEFAULT_ADVERTISE_PAGE.submit_button_text;
        }
    });
}

document.addEventListener("DOMContentLoaded", () => {
    renderAdvertisePage(advertisePageConfig);
    setupAdvertiseForm();
    loadAdvertisePageConfig();
});
