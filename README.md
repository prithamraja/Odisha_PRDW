This project has the following primary folders
  1. Ask - the backend files that process questions from the user and respond
  2. Insights - the backend files that generate insights
  3. frontend - all the frontend files
  4. Other_analysis - backend files for experimental analyses

In addition, the "Data" folder contains sample data for 20 GPs. "handoffs" contains markdown files and reports used to develop the system and "eval" contains evaluations. These folders do not feed into the functionality of the system and may be removed in production.

API keys are needed in two places
  1. Ask/.env - while the file has slots for several api keys, only the openAI ones are needed for now. Other keys exist to try out different models
  2. Insights/.env - once again, only openAI keys are needed. Since "Insights" is a batch process that only runs when data is updated, these keys are not needed while testing the system
