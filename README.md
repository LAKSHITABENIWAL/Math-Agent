# Math Routing Agent

A sophisticated mathematical problem-solving application that intelligently routes and solves various types of mathematical problems using specialized agents.

## Features

- **Intelligent Problem Analysis**: Automatically identifies the type of mathematical problem
- **Specialized Problem Solvers**: 
  - Arithmetic calculations
  - Linear equation solving
  - Derivative calculations
  - And more...
- **Web Search Integration**: Enhances problem-solving with web research capabilities
- **Real-time Feedback**: Interactive user feedback system
- **Modern React Frontend**: Clean and intuitive user interface

## Demo

https://drive.google.com/file/d/1das7siNOrRp9qbz7dUqvXTwpzAbMwNFx/view?usp=sharing




## Project Structure

```
├── frontend/               # React frontend application
│   ├── src/               # Source files
│   ├── public/            # Public assets
│   └── package.json       # Frontend dependencies
│
└── backend/               # Python FastAPI backend
    ├── app.py            # Main application server
    ├── arithmetic_helper.py
    ├── derivative_helper.py
    ├── linear_equation_solver.py
    └── requirements.txt   # Backend dependencies
```

## Technologies Used

### Frontend
- React.js
- Modern JavaScript (ES6+)
- CSS3

### Backend
- Python
- FastAPI
- SQLite
- Various mathematical libraries

## Getting Started

### Prerequisites
- Node.js (v14 or higher)
- Python (v3.8 or higher)
- npm or yarn

### Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd math-routing-agent
   ```

2. Set up the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   python app.py
   ```

3. Set up the frontend:
   ```bash
   cd frontend
   npm install
   npm start
   ```

4. Open your browser and navigate to `http://localhost:3000`

## How to Use

1. Enter your mathematical problem in the input field
2. The system will automatically analyze and route your problem to the appropriate solver
3. View the solution and explanation
4. Provide feedback if needed

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Special thanks to all contributors
- Mathematical libraries and frameworks used
- OpenAI for AI capabilities
