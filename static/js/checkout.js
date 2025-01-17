// Initialize Stripe.js
const stripe = Stripe('pk_test_51QXeJVHOaaPM28US4dCGqQkF0wkew9ZYvDWNb9dCNtQSkkRQTvOzhpvvte7cKheXMQuGq63n6DEdMR158Di629J500dMc4A5zX');

initialize();

// Fetch Checkout Session and retrieve the client secret
async function initialize() {
  const fetchClientSecret = async () => {
    const response = await fetch("/create-checkout-session", {
      method: "POST",
    });
    const { clientSecret } = await response.json();
    return clientSecret;
  };

  // Initialize Checkout
  const checkout = await stripe.initEmbeddedCheckout({
    fetchClientSecret,
  });

  // Mount Checkout
  checkout.mount('#checkout');
}