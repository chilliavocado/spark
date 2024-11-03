// register event to all action buttons
document.addEventListener("DOMContentLoaded", function () {
  // add events to all action buttons
  const likeButtons = document.getElementsByName("like");
  for (let i = 0; i < likeButtons.length; i++) {
    likeButtons[i].addEventListener("click", addExperience);
    likeButtons[i].addEventListener("click", toggleLike);
    likeButtons[i].setAttribute("tabindex", "0"); // Make div focusable
    likeButtons[i].setAttribute("role", "button"); // Set role for accessibility
  }

  // rate buttons
  const buyButtons = document.getElementsByName("buy");
  for (let i = 0; i < buyButtons.length; i++) {
    buyButtons[i].addEventListener("click", addExperience);
    buyButtons[i].setAttribute("tabindex", "0"); // Make div focusable
    buyButtons[i].setAttribute("role", "button"); // Set role for accessibility
  }

  // rate buttons
  const rateButtons = document.getElementsByName("rate");
  for (let i = 0; i < rateButtons.length; i++) {
    rateButtons[i].addEventListener("click", addExperience);
    rateButtons[i].addEventListener("click", rate);
    rateButtons[i].setAttribute("tabindex", "0"); // Make div focusable
    rateButtons[i].setAttribute("role", "button"); // Set role for accessibility
  }
});

// like button image toggle
function toggleLike(event) {
  const liked = event.target.classList.contains("like-on");
  likeProduct(event, !liked); // toggle status
}

function likeProduct(event, like = true) {
  event.target.className = like ? "like like-on" : "like";
}

// like button image toggle
function rate(event) {
  target = event.target;
  rating = parseInt(target.getAttribute("data-rating"), 10);
  pid = target.getAttribute("data-pid");

  rateProduct(rating, pid);
}

function rateProduct(rating, pid) {
  // style stars to display rating
  const rateButtons = document.getElementsByName("rate");
  for (let i = 0; i < rateButtons.length; i++) {
    rateButton = rateButtons[i];
    if (rateButton.getAttribute("data-pid") != pid) return;

    if (i < rating) {
      rateButton.className = "star star-on";
    } else {
      rateButton.className = "star";
    }
  }
}

// add experience to database for RL
function addExperience(event) {
  target = event.target;
  action = target.getAttribute("name");
  pid = target.getAttribute("data-pid");

  console.log(action + " product " + pid);

  switch (action) {
    case "like":
      break;
    case "buy":
      break;
    case "view":
      break;
    case "rate":
      break;
    default:
    // do nothing
  }
}
