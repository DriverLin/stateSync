import './App.css';
import useSyncDict from './components/useSyncDict';
import logo from './logo.svg';

function App() {
  
  const syncData = useSyncDict("ws://192.168.1.128:9999/ws")
  
  
  return (
    <div className="App">
      <header className="App-header">
        <img src={logo} className="App-logo" alt="logo" />
        <p>
          Edit <code>src/App.js</code> and save to reload.
        </p>
        <a
          className="App-link"
          href="https://reactjs.org"
          target="_blank"
          rel="noopener noreferrer"
        >
          {
            JSON.stringify(syncData)
          }
        </a>
      </header>
    </div>
  );
}

export default App;
