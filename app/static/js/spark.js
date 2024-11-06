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

  // Attach event listeners to product links for view tracking
  const productLinks = document.querySelectorAll(".product-view-link");
  productLinks.forEach((link) => {
    link.addEventListener("click", (event) => {
      const productId = link.getAttribute("data-pid"); // Fix by ensuring `link` reference
      const userId = getUserID();
      trackView(productId, userId);
    });
  });

  // Restore like status on load
  restoreLikeStatus();
});

// Track product view interaction
function trackView(productId, userId) {
  console.log("Product view:", productId, userId);
  sendInteraction("view", productId, userId);
}

// Like button handler
function handleLike(event) {
  const productId = event.target.getAttribute("data-pid");
  const userId = getUserID();
  const isLiked = toggleLike(event);

  // Set interaction value to 1 for like, 0 for unlike
  const value = isLiked ? 1 : 0;
  saveLikeStatus(productId, isLiked); // Persist like status
  sendInteraction("like", productId, userId, value);
}

// Save like status to localStorage for persisting per user and product
function saveLikeStatus(productId, isLiked) {
  const likes = JSON.parse(localStorage.getItem("likes") || "{}");
  likes[productId] = isLiked;
  localStorage.setItem("likes", JSON.stringify(likes));
}

// Restore like status from localStorage on load
function restoreLikeStatus() {
  const likes = JSON.parse(localStorage.getItem("likes") || "{}");
  const likeButtons = document.getElementsByName("like");
  likeButtons.forEach((button) => {
    const productId = button.getAttribute("data-pid");
    if (likes[productId]) {
      button.classList.add("like-on");
    }
  });
}

// Toggle like button style
function toggleLike(event) {
  const liked = event.target.classList.toggle("like-on");
  return liked;
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
  sendInteraction("rate", productId, userId, null, rating);
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

// Send interaction data to the API
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
