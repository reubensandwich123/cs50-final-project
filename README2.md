This project is a beginner-level application that I developed as the final project for Harvard’s CS50 course. It was a valuable learning experience where I applied foundational concepts in Python, Flask, HTML, CSS, and SQL to build a functional web application from scratch.

In addition to what I learned in CS50, I integrated Matplotlib and Pandas to handle data analysis and visualization — drawing from two separate courses I completed on data handling and Python libraries. This allowed me to experiment with plotting trends and summarizing data in a meaningful way within the application.

While the project meets its core objectives, I acknowledge that it has several limitations — particularly in terms of data storage structure, security, and performance efficiency. These are areas I aim to improve as I continue learning and refining my development skills.

Despite the imperfections, I’ve chosen to share this project publicly as a reflection of my current capabilities, growth mindset and ambition. 

Things to work on:
- Handling conflicts between uploads of different users
- Encrypting information of user uploads
- Balance history sometimes not working, when uploaded wrong file
- Latest analysis overview unclear whether it's for latest upload or latest date


Areas of my project that I have improved:
- Fixed issue where unique constraint violated due to multiple users uploading statement for the same date
- Fixed issue where unique constraint violated due to the user analyzing both IDS and IWS, or each one multiple times
- Multiple users will be able to store balance entries even if their balances are the same, as the unique constraint is applied to the combination of user_id and date, not the balance value itself.

