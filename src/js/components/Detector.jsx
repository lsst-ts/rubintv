import React from 'react';
import { useState, useEffect, useRef } from 'react';
import detectorMap from '../data/detectorMap.json';
import cwfsMap from '../data/cwfsMap.json';

// Get status class name
const getStatusClass = (status) => {
  switch(status) {
    case 'free': return 'status-free';
    case 'busy': return 'status-busy';
    case 'queued': return 'status-queued';
    default: return 'status-missing';
  }
};

const DetectorSection = ({ title, map, statuses, size = 'large' }) => {
  return (
    <div className={`detector-section detector-section-${size}`}>
      <h2 className="detector-title">{title}</h2>
      <DetectorCanvas
        detectorMap={map}
        detectorStatuses={statuses}
        size={size}
      />
    </div>
  );
};

const DetectorRow = ({ children }) => {
  return (
    <div className="detector-row">
      {children}
    </div>
  );
};

const DetectorStatusVisualization = () => {
  const [mainDetectorStatuses, setMainDetectorStatuses] = useState({
    sfmSet0: {},
    sfmSet1: {},
    sfbStep1b: [],
    backlogWorkers: []
  });
  const [cwfsStatuses, setCwfsStatuses] = useState({
    aosSet0: {},
    aosSet1: {},
    aosSet2: {},
    aosSet3: {},
    aosStep1b: []
  });

  // For demo purposes, let's create some sample statuses for detectors
  const generateRandomStatuses = (detectorIds) => {
    const statuses = {};
    const statusOptions = ['free', 'busy', 'queued', 'missing'];

    detectorIds.forEach(id => {
      const statusIndex = Math.floor(Math.random() * 4);
      const status = statusOptions[statusIndex];

      statuses[id] = {
        status,
        queue_length: status === 'queued' ? Math.floor(Math.random() * 10) + 1 : 0
      };
    });

    return statuses;
  };

  // Generate random statuses for step1b and backlog cells
  const generateCells = (count) => {
    const statusOptions = ['free', 'busy', 'queued', 'missing'];
    return Array(count).fill().map(() => {
      const statusIndex = Math.floor(Math.random() * 4);
      const status = statusOptions[statusIndex];
      return {
        status,
        queue_length: status === 'queued' ? Math.floor(Math.random() * 10) + 1 : 0
      };
    });
  };

  useEffect(() => {
    const mainDetectorIds = Object.keys(detectorMap);
    const cwfsDetectorIds = Object.keys(cwfsMap);

    setMainDetectorStatuses({
      sfmSet0: generateRandomStatuses(mainDetectorIds),
      sfmSet1: generateRandomStatuses(mainDetectorIds),
      sfbStep1b: generateCells(5),
      backlogWorkers: generateCells(8)
    });

    setCwfsStatuses({
      aosSet0: generateRandomStatuses(cwfsDetectorIds),
      aosSet1: generateRandomStatuses(cwfsDetectorIds),
      aosSet2: generateRandomStatuses(cwfsDetectorIds),
      aosSet3: generateRandomStatuses(cwfsDetectorIds),
      aosStep1b: generateCells(5)
    });
  }, []);

  return (
    <div className="detector-container">
      <div className="main-detectors">
        <DetectorSection
          title="SMF Worker Set 1"
          map={detectorMap}
          statuses={mainDetectorStatuses.sfmSet0}
          size="large"
        />
        <DetectorSection
          title="SMF Worker Set 2"
          map={detectorMap}
          statuses={mainDetectorStatuses.sfmSet1}
          size="large"
        />
      </div>
      <div className="aos-detectors">
        <DetectorSection
          title="AOS Worker Set 1"
          map={cwfsMap}
          statuses={cwfsStatuses.aosSet0}
          size="small"
        />
        <DetectorSection
          title="AOS Worker Set 2"
          map={cwfsMap}
          statuses={cwfsStatuses.aosSet1}
          size="small"
        />
        <DetectorSection
          title="AOS Worker Set 3"
          map={cwfsMap}
          statuses={cwfsStatuses.aosSet2}
          size="small"
        />
        <DetectorSection
          title="AOS Worker Set 4"
          map={cwfsMap}
          statuses={cwfsStatuses.aosSet3}
          size="small"
        />
      </div>
      <div className="step1b-section">
        <div className="step1b-groups">
          <div className="step1b-row">
            <h3>SFB Step 1b</h3>
            <div className="step1b-cells">
              {mainDetectorStatuses.sfbStep1b.map((status, i) => (
                <div
                  key={`sfb-step1b-${i}`}
                  className={`detector-cell ${getStatusClass(status.status)}`}
                >
                  {status.status === 'queued' && (
                    <div className="queue-length">{status.queue_length}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
          <div className="step1b-row">
            <h3>AOS Step 1b</h3>
            <div className="step1b-cells">
              {cwfsStatuses.aosStep1b.map((status, i) => (
                <div
                  key={`aos-step1b-${i}`}
                  className={`detector-cell ${getStatusClass(status.status)}`}
                >
                  {status.status === 'queued' && (
                    <div className="queue-length">{status.queue_length}</div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
        <div className="backlog-row">
          <h3>Backlog Workers</h3>
          <div className="step1b-cells">
            {mainDetectorStatuses.backlogWorkers.map((status, i) => (
              <div
                key={`backlog-worker-${i}`}
                className={`detector-cell ${getStatusClass(status.status)}`}
              >
                {status.status === 'queued' && (
                  <div className="queue-length">{status.queue_length}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="legend">
        <div className="legend-items">
          <div className="legend-item">
            <div className="legend-color status-free"></div>
            <span>Free</span>
          </div>
          <div className="legend-item">
            <div className="legend-color status-busy"></div>
            <span>Busy</span>
          </div>
          <div className="legend-item">
            <div className="legend-color status-queued"></div>
            <span>Queued</span>
          </div>
          <div className="legend-item">
            <div className="legend-color status-missing"></div>
            <span>Missing</span>
          </div>
        </div>
      </div>
    </div>
  );
};

const DetectorCanvas = ({ detectorMap, detectorStatuses }) => {
  const containerRef = useRef(null);
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 });

  useEffect(() => {
    const updateDimensions = () => {
      if (containerRef.current) {
        const rect = containerRef.current.getBoundingClientRect();
        setDimensions({
          width: rect.width,
          height: rect.width  // Keep it square
        });
      }
    };

    updateDimensions();
    window.addEventListener('resize', updateDimensions);
    return () => window.removeEventListener('resize', updateDimensions);
  }, []);

  const { width, height } = dimensions;
  const padding = Math.min(width, height) * 0.05; // 5% padding

  // Find the min and max values for x and y to calculate scaling
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;

  Object.values(detectorMap).forEach(detector => {
    if (detector.corners) {
      const corners = detector.corners;
      [corners.upperLeft, corners.upperRight, corners.lowerLeft, corners.lowerRight].forEach(corner => {
        minX = Math.min(minX, corner[0]);
        maxX = Math.max(maxX, corner[0]);
        minY = Math.min(minY, corner[1]);
        maxY = Math.max(maxY, corner[1]);
      });
    }
  });

  // Calculate scale factors to fit the data into the canvas
  const dataWidth = maxX - minX;
  const dataHeight = maxY - minY;
  const scale = Math.min(
    (width - 2 * padding) / dataWidth,
    (height - 2 * padding) / dataHeight
  );

  // Function to convert data coordinates to canvas coordinates
  const toCanvasX = (x) => (x - minX) * scale + padding;
  const toCanvasY = (y) => (maxY - y) * scale + padding;

  if (width === 0) return <div ref={containerRef} className="detector-canvas" />;

  return (
    <div ref={containerRef} className="detector-canvas">
      {Object.entries(detectorMap).map(([id, detector]) => {
        if (!detector.corners) return null;
        
        const status = detectorStatuses[id] || { status: 'unknown', queue_length: 0 };
        const { corners } = detector;

        const canvasCorners = {
          upperLeft: [toCanvasX(corners.upperLeft[0]), toCanvasY(corners.upperLeft[1])],
          upperRight: [toCanvasX(corners.upperRight[0]), toCanvasY(corners.upperRight[1])],
          lowerLeft: [toCanvasX(corners.lowerLeft[0]), toCanvasY(corners.lowerLeft[1])],
          lowerRight: [toCanvasX(corners.lowerRight[0]), toCanvasY(corners.lowerRight[1])]
        };

        const left = Math.min(canvasCorners.upperLeft[0], canvasCorners.lowerLeft[0]);
        const top = Math.min(canvasCorners.upperLeft[1], canvasCorners.upperRight[1]);
        const right = Math.max(canvasCorners.upperRight[0], canvasCorners.lowerRight[0]);
        const bottom = Math.max(canvasCorners.lowerLeft[1], canvasCorners.lowerRight[1]);

        const cellWidth = right - left;
        const cellHeight = bottom - top;
        const fontSize = Math.max(8, Math.min(cellWidth / 3, cellHeight / 3, 14));

        return (
          <div
            key={id}
            className={`detector-cell ${getStatusClass(status.status)}`}
            style={{
              position: 'absolute',
              left: `${left}px`,
              top: `${top}px`,
              width: `${cellWidth}px`,
              height: `${cellHeight}px`
            }}>
            <div className="detector-cell-content">
              {status.status === 'queued' && (
                <div className="queue-length" style={{ fontSize: `${fontSize}px` }}>
                  {status.queue_length}
                </div>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default DetectorStatusVisualization;
