# Push to GitHub

Your **backend** and **frontend** are committed locally. To create the GitHub repo and push:

## 1. Create the repo on GitHub

- Open: **https://github.com/new**
- **Repository name:** `pipelineom`
- Leave "Add a README" **unchecked**
- Click **Create repository**

## 2. Add remote and push

Run these in the project root (replace `YOUR_USERNAME` with your GitHub username):

```bash
cd /Users/krasimirkirilov/Desktop/pipelineom
git remote add origin https://github.com/YOUR_USERNAME/pipelineom.git
git push -u origin main
```

If you use SSH:

```bash
git remote add origin git@github.com:YOUR_USERNAME/pipelineom.git
git push -u origin main
```

Done. Your `backend/` and `frontend/` folders will be on GitHub.
