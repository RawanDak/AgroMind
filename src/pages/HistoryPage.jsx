import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "../components/Navbar";
import "./HistoryPage.css";

function HistoryPage() {
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [sortOrder, setSortOrder] = useState("newest");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  const navigate = useNavigate();

  const limit = 20;
  const totalPages = Math.ceil(total / limit);

  useEffect(() => {
    const token = localStorage.getItem("token");

    setLoading(true);

    fetch(
      `${import.meta.env.VITE_API_URL}/history?skip=${
        (page - 1) * limit
      }&limit=${limit}&sort=${sortOrder}`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      },
    )
      .then((response) => response.json())
      .then((data) => {
        setHistory(data.items);
        setTotal(data.total);
        setLoading(false);
      })
      .catch((error) => {
        console.error("Error loading history:", error);
        setLoading(false);
      });
  }, [page, sortOrder]);

  const filteredHistory = history.filter((item) => {
    const search = searchTerm.toLowerCase();

    return (
      item.crop?.toLowerCase().includes(search) ||
      item.disease_name?.toLowerCase().includes(search)
    );
  });

  return (
    <div className="history-page">
      <Navbar />

      <main className="history-card">
        <h1>Scan History</h1>

        <div className="history-controls">
          <input
            type="text"
            placeholder="Search crop or disease..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />

          <select
            value={sortOrder}
            onChange={(e) => {
              setSortOrder(e.target.value);
              setPage(1);
            }}
          >
            <option value="newest">Newest First</option>
            <option value="oldest">Oldest First</option>
          </select>
        </div>

        {loading ? (
          <p>Loading history...</p>
        ) : filteredHistory.length === 0 ? (
          <p>No scans found.</p>
        ) : (
          <div className="history-list">
            {filteredHistory.map((item) => (
              <div
                className="history-item"
                key={item.diagnosis_id}
                onClick={() => navigate(`/history/${item.diagnosis_id}`)}
              >
                <h3>
                  {item.crop} — {item.disease_name}
                </h3>

                <p>
                  <strong>Severity:</strong> {item.severity}
                </p>

                <p>
                  <strong>Status:</strong> {item.status}
                </p>

                <p>
                  <strong>Confidence:</strong> {item.confidence}
                </p>

                <small>{new Date(item.created_at).toLocaleString()}</small>
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="pagination">
            <button disabled={page === 1} onClick={() => setPage(page - 1)}>
              Previous
            </button>

            <span>
              Page {page} of {totalPages}
            </span>

            <button
              disabled={page === totalPages}
              onClick={() => setPage(page + 1)}
            >
              Next
            </button>
          </div>
        )}
      </main>
    </div>
  );
}

export default HistoryPage;
