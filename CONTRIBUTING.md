# Contributing to elastix-api

First off, thanks for taking the time to contribute! 🎉

**elastix-api** is a prototype and case study project. Whether you're fixing a bug, improving the UI, or suggesting a new simulation logic, your help is welcome. We want to keep this project fun and educational.

## 🚀 How to get started

1.  **Check the Issues**: Look for existing issues or create a new one to discuss what you want to change.
2.  **Fork the Repository**: Create your own copy of the project on GitHub.
3.  **Clone it**:
    ```bash
    git clone [https://github.com/YOUR-USERNAME/elastix-api.git](https://github.com/YOUR-USERNAME/elastix-api.git)
    cd elastix-api
    npm install
    ```
4.  **Backend (Optional but recommended)**: If you are working on data fetching or simulations, make sure to have the `elastix-api-api` running via Docker.

## 🛠 Development Workflow

We follow a simple feature-branch workflow.

1.  **Create a Branch**: Please include the issue reference in your branch name:
    ```bash
    # Example for Issue #42
    git checkout -b feature/42
    ```
2.  **Code**: We use **React 18**, **TypeScript**, and **Tailwind CSS**.
    * Please use `shadcn/ui` components where possible to maintain the design system.
    * Keep feature-specific logic in `src/items/`.
3.  **Test & Lint**: Before you commit, make sure everything is clean:
    ```bash
    npm run lint
    npm run test
    ```
4.  **Commit**: Write clear, concise commit messages.
    * *Good:* "Fix layout issue in Segmentation chart"
    * *Bad:* "fix css"

## 📮 Submitting a Pull Request (PR)

1.  Push your branch to your fork.
2.  Open a Pull Request against the `main` branch of `elastix-api`.
3.  Describe your changes in the PR description.
4.  Wait for a review! I usually try to review PRs within a few days.

## 🤝 Code of Conduct

Be respectful and kind to others. We are all here to learn and build cool stuff.

Happy Coding! 🚀
