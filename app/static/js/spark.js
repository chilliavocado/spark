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

  // Track product views only when they are actually interacted with
});

// Like button handler
function handleLike(event) {
  const productId = event.target.getAttribute("data-pid");
  toggleLike(event);
  sendInteraction("like", productId);
}

// Toggle like button style
function toggleLike(event) {
  const liked = event.target.classList.contains("like-on");
  event.target.className = liked ? "like" : "like like-on";
}

// Buy button handler
function handleBuy(event) {
  const productId = event.target.getAttribute("data-pid");
  sendInteraction("buy", productId);
}

// Rate button handler
function handleRate(event) {
  const rating = parseInt(event.target.getAttribute("data-rating"), 10);
  const productId = event.target.getAttribute("data-pid");
  updateRatingDisplay(rating, productId);
  sendInteraction("rate", productId, rating);
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

// Send interaction data to backend
function sendInteraction(action, productId, value = null) {
  const interactionData = {
    user_id: 1, // Replace with dynamic user ID if applicable
    product_id: parseInt(productId),
    interaction_type: action,
    value: value,
    timestamp: new Date().toISOString(),
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
      }
    })
    .catch((error) => {
      console.error("Network error logging interaction:", error);
    });
}
