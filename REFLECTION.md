### DISCOUNT COUPONS
## QUESTION 01
    One decision from grill me that led to an important decision on how the coupons are tracked, displayed, promoted, and regarded by the codebase was the timezone used by the store to manage the use of the coupon codes. I was debating between using the stores local timezone to dictate coupon requirements and leaving the store on UTC time and having a separate clock for the coupons to only use their own time zone setting. I felt both options were worth implementing but knew that having two separate clocks used by the store is redundant and can just be communicated that the coupons follow the stores local time which I have set to U.S. Central time.

##  QUESTION 02
    The change I made after implementing the feautre was due to my own user experience. I was manually reviewing the implemented feature on the website, and wasn't wearing my glasses so I couldnt tell there was a discount code feature added within the first few seconds of looking at it. The change originally blended in with other checkout variables and if I hadn't known any better I would say there wasn't a noticable change to the checkout process. After the change had been implemented there is now a bright blue heading asking if the customer has a discount code, this is drastically different styling than any other components displayed on the checkout page so the coupon box stands out and is easier to see for all customers.















## QUESTION 01
    Marking a product as featured in the admin interface causes the badge to appear on the product details and main catalog pages of the site. This badge is displayed with the optional "unavailable" badge as well as the catagory badge shown on all products. the admin checkbox in products/admin.py, after checking the box and saving the change it sets product.is_featured = True. When the storefront is accessed by a shopper, for the catalog page the view loads the products and passes them to the corresponding template. For the detail page the view loads the product and passes it to the template. The detail and catalog templates then verify the featured status of each product, if the product is featured the badge is displayed on each page. The styling for the badge is comprised of DaisyUI classes which tailwind compiles into CSS.

## QUESTION 02
    I confirmed the feature works by first running the tests the agent created to assert if marked featured products were actually featured and vice versa for unfeatured products. After that I ran the server and verified that the badge appeared on the products I edited through the admin interface, ensuring the badge was displayed on the main catalog page and each products detail page.

## QUESTION 03
    One unexpected challenge I had was accessing the admin interface, I believe asking the agent about it helped me get unstuck or realize what I had to do; the user admin was already logged into an account and said I did not have permission to access the admin interface. After logging out and using the superuser defined in the codebase I was able to access the admin controls. While the agents response didn't tell me exactly what I needed to do as I didn't explain the issue I was having specifically, I realized after logging out how the superuser connects and is implemented into the codebase as well as the various components of the administrative process.