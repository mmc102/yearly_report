# Big picture

this started as a project to generate my yearly financial report using haskell
and has evolved a bit to be a [simple webapp](https://myfinancereport.com/).
I actually rewrote it in react + fastapi, so that is currently what you see on the site.

# Features

- parse PDF bank statements and credit card statements
- categorize expenses
- generate reports
  - per month drill down
  - summary -> per transaction drill down
  - configurable sankey and column diagrams
- allow for manually update transactions from a ui

# Tech

- haskell for backend and webserver
- html for report
- postgres to persist data
- LLM for PDF parsing (using structured outputs)
- LLM for categorization (using structured outputs)

# Disclaimer

this is mainly a project through which I will learn more about haskell, but I expect the code to be bad.


# User feedback / TODO

big milestones before launch:

-> Stripe
  --> sort of exists but needs more work
-> Plaid
  -> bug where i got logged off after plaid
-> Email

-> worker should be a lambda

-> TODO get delete to work on app

-> need to update the how does this work page 

-> would be nice to have some tests around user creation

-> add a last active at time on the user model

-> shareable report

-> running grant to sequence after a new table: 
  GRANT USAGE, UPDATE ON SEQUENCE plaid_item_id_seq TO app_user;
  GRANT USAGE, UPDATE ON SEQUENCE plaid_account_id_seq TO app_user;
  GRANT USAGE, UPDATE ON SEQUENCE plaid_sync_log_id_seq TO app_user;

-> redirect everything to the main url

-> welcome email

-> merge account function
--> built backend but needs frontend

-> repro filter bug by getting a query that has no results

-> nice to have: search

-> try to prevent color overlaps

-> dashboard config and ability to save them (query params)
--> parse the query params from the url

-> you cant remove a category once it is used
--> doesnt rerun on category delete

-> Expense should line up in the table


