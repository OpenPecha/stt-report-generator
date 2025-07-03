# STT Report Generator

<h1 align="center">
  <br>
  <a href="https://openpecha.org"><img src="https://avatars.githubusercontent.com/u/82142807?s=400&u=19e108a15566f3a1449bafb03b8dd706a72aebcd&v=4" alt="OpenPecha" width="150"></a>
  <br>
</h1>

## Speech-to-Text Transcription Report Generator
Automatically generate weekly reports from your STT transcription database using GitHub Actions

## Owner(s)

- [@ngawangtrinley](https://github.com/ngawangtrinley)
- [@mikkokotila](https://github.com/mikkokotila)
- [@evanyerburgh](https://github.com/evanyerburgh)


## Table of contents
<p align="center">
  <a href="#project-description">Project description</a> •
  <a href="#who-this-project-is-for">Who this project is for</a> •
  <a href="#project-dependencies">Project dependencies</a> •
  <a href="#instructions-for-use">Instructions for use</a> •
  <a href="#contributing-guidelines">Contributing guidelines</a> •
  <a href="#additional-documentation">Additional documentation</a> •
  <a href="#how-to-get-help">How to get help</a> •
  <a href="#terms-of-use">Terms of use</a>
</p>
<hr>

## Project description

With STT Report Generator, you can automatically generate weekly reports from your speech-to-text transcription database. This tool connects to your database, extracts key metrics about your transcription tasks, and generates both CSV data files and markdown summary reports. The entire process is automated using GitHub Actions, which can be scheduled to run on a regular basis.


## Who this project is for
This project is intended for team members and managers who need regular reports on speech-to-text transcription progress without manual data extraction and analysis.


## Project dependencies
Before using STT Report Generator, ensure you have:
* A GitHub account with access to create repository secrets
* A database containing STT transcription tasks data
* Database credentials with read access to the transcription data


## Instructions for use
Get started with STT Report Generator by setting up the GitHub Actions workflow and database connection.

### Set up GitHub Actions
1. Fork or clone this repository

2. Set up your database connection secrets
   
   a. Go to your repository's Settings > Secrets > Actions
   
   b. Create the following secrets for your PostgreSQL database:
      - `HOST` - Your database host (e.g., dpg-xxxxxx.oregon-postgres.render.com)
      - `DBNAME` - Your database name
      - `DBUSER` - Your database username
      - `PASSWORD` - Your database password

3. Customize the database query (if needed)
   
   Open `generate_report.py` and modify the `query_transcription_data()` function to match your database schema.

### Configure Report Schedule
1. Adjust the schedule in `.github/workflows/report-generator.yml`
   
   The default setting runs every Monday at 9:00 AM UTC:
   ```yaml
   schedule:
     - cron: '0 9 * * 1'  # Every Monday at 9AM UTC
   ```
   
   You can modify this cron expression to change the schedule.

### Run the Report Generator
1. Manual trigger:
   
   a. Go to the Actions tab in your repository
   
   b. Select the "Weekly STT Report Generation" workflow
   
   c. Click "Run workflow"

2. Automatic schedule:
   
   Reports will automatically generate according to your configured schedule


### Troubleshooting

<table>
  <tr>
   <td>
    Issue
   </td>
   <td>
    Solution
   </td>
  </tr>
  <tr>
   <td>
    Workflow fails with database connection error
   </td>
   <td>
    Check that your DATABASE_URL secret is correctly formatted and that the database is accessible from GitHub Actions
   </td>
  </tr>
  <tr>
   <td>
    Query fails with column not found error
   </td>
   <td>
    Modify the query in generate_report.py to match your database schema
   </td>
  </tr>
  <tr>
   <td>
    Reports not appearing in repository
   </td>
   <td>
    Check the Actions tab for workflow run logs and ensure GitHub Actions has write permissions to your repository
   </td>
  </tr>
</table>


## Contributing guidelines
If you'd like to help out, check out our [contributing guidelines](/CONTRIBUTING.md).


## Additional documentation

For more information:
* [GitHub Actions Documentation](https://docs.github.com/en/actions)
* [Cron Syntax Reference](https://crontab.guru/)
* [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)


## How to get help
* File an issue.
* Email us at openpecha[at]gmail.com.
* Join our [discord](https://discord.com/invite/7GFpPFSTeA).


## Terms of use
_Project Name_ is licensed under the [MIT License](/LICENSE.md).
