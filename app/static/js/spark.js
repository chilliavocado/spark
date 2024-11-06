// static/js/spark.js

// Set or retrieve user ID (e.g., retrieved upon login)
function setUserID(userId) {
  localStorage.setItem("user_id", userId);
}

// Get the current user ID; if not set, default to 1
function getUserID() {
  return localStorage.getItem("user_id") || 1;
}

// Register event to all action buttons once the DOM is loaded
document.addEventListener("DOMContentLoaded", function () {
  // Attach event listeners for action buttons
  const likeButtons = document.getElementsByName("like");
  likeButtons.forEach((button) => {
    button.addEventListener("click", handleLike);
    button.setAttribute("tabindex", "0");
    button.setAttribute("role", "button");
  });

  const buyButtons = document.getElementsByName("buy");
  buyButtons.forEach((button) => {
    button.addEventListener("click", handleBuy);
    button.setAttribute("tabindex", "0");
    button.setAttribute("role", "button");
  });

  const rateButtons = document.getElementsByName("rate");
  rateButtons.forEach((button) => {
    button.addEventListener("click", handleRate);
    button.setAttribute("tabindex", "0");
    button.setAttribute("role", "button");
  });
});

// Like button handler
function handleLike(event) {
  const productId = event.target.getAttribute("data-pid");
  const userId = getUserID();
  toggleLike(event);
  sendInteraction("like", productId, userId);
}

// Buy button handler
function handleBuy(event) {
  const productId = event.target.getAttribute("data-pid");
  const userId = getUserID();
  sendInteraction("buy", productId, userId);
}

// Rate button handler
function handleRate(event) {
  const rating = parseInt(event.target.getAttribute("data-rating"), 10);
  const productId = event.target.getAttribute("data-pid");
  const userId = getUserID();
  updateRatingDisplay(rating, productId);
  sendInteraction("rate", productId, userId, rating);
}

// Toggle like button style
function toggleLike(event) {
  const liked = event.target.classList.contains("like-on");
  event.target.className = liked ? "like" : "like like-on";
}

// Update rating display stars
function updateRatingDisplay(rating, productId) {
  const rateButtons = document.querySelectorAll(
    `[data-pid="${productId}"][name="rate"]`
  );
  rateButtons.forEach((button, index) => {
    button.className = index < rating ? "star star-on" : "star";
  });
}

function sendInteraction(
  action,
  productId,
  userId,
  value = null,
  reviewScore = null,
  zipCode = null,
  city = null,
  state = null
) {
  const interactionData = {
    user_id: parseInt(userId),
    product_id: parseInt(productId),
    interaction_type: action,
    value: value,
    review_score: reviewScore,
    zip_code: zipCode,
    city: city,
    state: state,
  };

  fetch("/api/interaction", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(interactionData),
  })
    .then((response) => {
      if (!response.ok) {
        console.error("Error logging interaction:", response.statusText);
      } else {
        console.log("Interaction saved successfully");
      }
    })
    .catch((error) => {
      console.error("Network error logging interaction:", error);
    });
}
