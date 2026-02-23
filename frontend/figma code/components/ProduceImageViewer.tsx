import { useState, useRef, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { 
  Image as ImageIcon,
  Camera,
  RefreshCw,
  Maximize2,
  Download,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Eye,
  EyeOff
} from "lucide-react";
import { ProduceItem, Detection } from "../App";

interface ProduceImageViewerProps {
  produce: ProduceItem;
  onMLUpdate: (produceId: string, detections: Detection[]) => void;
}

export function ProduceImageViewer({ produce, onMLUpdate }: ProduceImageViewerProps) {
  const [showDetections, setShowDetections] = useState(true);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const imageRef = useRef<HTMLImageElement>(null);

  // Simulate ML analysis
  const handleRunAnalysis = () => {
    setIsAnalyzing(true);
    
    // Simulate API call to ML backend
    setTimeout(() => {
      // Generate random detections for demo
      const mockDetections: Detection[] = [
        {
          id: `det-${Date.now()}-1`,
          label: `${produce.name} - ${Math.random() > 0.5 ? 'Good Quality' : 'Minor Issues'}`,
          confidence: 80 + Math.random() * 20,
          boundingBox: {
            x: 10 + Math.random() * 30,
            y: 10 + Math.random() * 30,
            width: 20 + Math.random() * 20,
            height: 20 + Math.random() * 20
          },
          status: Math.random() > 0.7 ? 'warning' : 'good'
        },
        {
          id: `det-${Date.now()}-2`,
          label: `${produce.name} - ${Math.random() > 0.3 ? 'Good Quality' : 'Spoiled'}`,
          confidence: 70 + Math.random() * 30,
          boundingBox: {
            x: 40 + Math.random() * 30,
            y: 30 + Math.random() * 30,
            width: 20 + Math.random() * 20,
            height: 20 + Math.random() * 20
          },
          status: Math.random() > 0.8 ? 'bad' : 'good'
        }
      ];

      onMLUpdate(produce.id, mockDetections);
      setIsAnalyzing(false);
    }, 2000);
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'good':
        return <CheckCircle2 className="h-5 w-5 text-green-600" />;
      case 'warning':
        return <AlertTriangle className="h-5 w-5 text-yellow-600" />;
      case 'bad':
        return <XCircle className="h-5 w-5 text-red-600" />;
      default:
        return <Camera className="h-5 w-5 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'good':
        return 'bg-green-100 text-green-800 border-green-200';
      case 'warning':
        return 'bg-yellow-100 text-yellow-800 border-yellow-200';
      case 'bad':
        return 'bg-red-100 text-red-800 border-red-200';
      default:
        return 'bg-gray-100 text-gray-800 border-gray-200';
    }
  };

  const getDetectionBoxColor = (status: string) => {
    switch (status) {
      case 'good':
        return '#22c55e';
      case 'warning':
        return '#eab308';
      case 'bad':
        return '#ef4444';
      default:
        return '#9ca3af';
    }
  };

  return (
    <Card className="w-full">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <Camera className="h-5 w-5" />
            {produce.name} - Quality Analysis
          </CardTitle>
          <div className="flex items-center gap-2">
            <Badge className={getStatusColor(produce.status)}>
              <div className="flex items-center gap-1">
                {getStatusIcon(produce.status)}
                {produce.status.charAt(0).toUpperCase() + produce.status.slice(1)}
              </div>
            </Badge>
            {produce.confidence > 0 && (
              <Badge variant="outline">
                {produce.confidence.toFixed(0)}% Confidence
              </Badge>
            )}
          </div>
        </div>

        {/* Bad Items Summary */}
        {produce.detections && produce.detections.length > 0 && (
          <div className="mt-3 bg-gradient-to-r from-red-50 to-orange-50 border border-red-200 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="p-2 bg-red-100 rounded-full">
                  <XCircle className="h-5 w-5 text-red-600" />
                </div>
                <div>
                  <p className="text-sm font-medium text-red-900">
                    {produce.detections.filter(d => d.status === 'bad').length} Bad Item{produce.detections.filter(d => d.status === 'bad').length !== 1 ? 's' : ''}
                  </p>
                  <p className="text-xs text-red-700">
                    Out of {produce.detections.length} detected item{produce.detections.length !== 1 ? 's' : ''} in inventory
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-2xl font-bold text-red-600">
                  {produce.detections.length > 0 
                    ? Math.round((produce.detections.filter(d => d.status === 'bad').length / produce.detections.length) * 100)
                    : 0}%
                </p>
                <p className="text-xs text-red-700">Bad Rate</p>
              </div>
            </div>
            
            {/* Quality breakdown */}
            <div className="mt-3 pt-3 border-t border-red-200 flex gap-4 text-xs">
              <div className="flex items-center gap-1">
                <CheckCircle2 className="h-3 w-3 text-green-600" />
                <span className="text-gray-700">
                  {produce.detections.filter(d => d.status === 'good').length} Good
                </span>
              </div>
              <div className="flex items-center gap-1">
                <AlertTriangle className="h-3 w-3 text-yellow-600" />
                <span className="text-gray-700">
                  {produce.detections.filter(d => d.status === 'warning').length} Warning
                </span>
              </div>
              <div className="flex items-center gap-1">
                <XCircle className="h-3 w-3 text-red-600" />
                <span className="text-gray-700">
                  {produce.detections.filter(d => d.status === 'bad').length} Bad
                </span>
              </div>
            </div>
          </div>
        )}
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Image Display with ML Detections */}
        <div className="relative bg-gray-900 rounded-lg overflow-hidden">
          <div className="relative aspect-video">
            <img
              ref={imageRef}
              src={produce.image_url}
              alt={produce.name}
              className="w-full h-full object-cover"
              crossOrigin="anonymous"
            />
            
            {/* ML Detection Overlays */}
            {showDetections && produce.detections && produce.detections.length > 0 && (
              <svg
                className="absolute inset-0 w-full h-full pointer-events-none"
                viewBox="0 0 100 100"
                preserveAspectRatio="none"
              >
                {produce.detections.map((detection) => (
                  <g key={detection.id}>
                    {/* Bounding Box */}
                    <rect
                      x={detection.boundingBox.x}
                      y={detection.boundingBox.y}
                      width={detection.boundingBox.width}
                      height={detection.boundingBox.height}
                      fill="none"
                      stroke={getDetectionBoxColor(detection.status)}
                      strokeWidth="0.5"
                      className="animate-pulse"
                    />
                    {/* Label Background */}
                    <rect
                      x={detection.boundingBox.x}
                      y={detection.boundingBox.y - 4}
                      width={detection.boundingBox.width}
                      height="4"
                      fill={getDetectionBoxColor(detection.status)}
                      opacity="0.9"
                    />
                    {/* Label Text */}
                    <text
                      x={detection.boundingBox.x + 1}
                      y={detection.boundingBox.y - 1}
                      fill="white"
                      fontSize="2"
                      fontWeight="bold"
                    >
                      {detection.confidence.toFixed(0)}%
                    </text>
                  </g>
                ))}
              </svg>
            )}

            {/* Analysis Loading Overlay */}
            {isAnalyzing && (
              <div className="absolute inset-0 bg-black/60 flex items-center justify-center">
                <div className="text-white text-center">
                  <RefreshCw className="h-12 w-12 mx-auto mb-3 animate-spin" />
                  <p className="text-lg">Running ML Analysis...</p>
                  <p className="text-sm text-gray-300 mt-1">Detecting quality indicators</p>
                </div>
              </div>
            )}
          </div>

          {/* Image Controls */}
          <div className="absolute bottom-2 left-2 flex gap-2">
            <Button
              size="sm"
              variant="secondary"
              onClick={handleRunAnalysis}
              disabled={isAnalyzing}
            >
              <RefreshCw className={`h-3 w-3 ${isAnalyzing ? 'animate-spin' : ''}`} />
            </Button>
            <Button
              size="sm"
              variant="secondary"
              onClick={() => setShowDetections(!showDetections)}
            >
              {showDetections ? <EyeOff className="h-3 w-3" /> : <Eye className="h-3 w-3" />}
            </Button>
            <Button size="sm" variant="secondary">
              <Maximize2 className="h-3 w-3" />
            </Button>
            <Button size="sm" variant="secondary">
              <Download className="h-3 w-3" />
            </Button>
          </div>

          {/* Detection Count Badge */}
          {produce.detections && produce.detections.length > 0 && (
            <div className="absolute top-2 right-2">
              <Badge className="bg-black/70 text-white border-white/20">
                {produce.detections.length} Detection{produce.detections.length !== 1 ? 's' : ''}
              </Badge>
            </div>
          )}
        </div>

        {/* Produce Information */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-1">Category</p>
            <p className="font-medium">{produce.category}</p>
          </div>
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs text-muted-foreground mb-1">Quantity</p>
            <p className="font-medium">{produce.quantity} units</p>
          </div>
          {produce.price && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-1">Price</p>
              <p className="font-medium">${produce.price.toFixed(2)}</p>
            </div>
          )}
          {produce.supplier && (
            <div className="bg-gray-50 rounded-lg p-3">
              <p className="text-xs text-muted-foreground mb-1">Supplier</p>
              <p className="font-medium truncate" title={produce.supplier}>{produce.supplier}</p>
            </div>
          )}
        </div>

        <Separator />

        {/* Detection Details */}
        {produce.detections && produce.detections.length > 0 && (
          <div className="space-y-3">
            <h4 className="font-medium flex items-center gap-2">
              <CheckCircle2 className="h-4 w-4" />
              Detection Results
            </h4>
            <div className="space-y-2 max-h-64 overflow-y-auto">
              {produce.detections.map((detection, index) => (
                <div 
                  key={detection.id}
                  className="border rounded-lg p-3 hover:bg-gray-50 transition-colors"
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2">
                      {getStatusIcon(detection.status)}
                      <span className="text-sm font-medium">Detection #{index + 1}</span>
                    </div>
                    <Badge className={getStatusColor(detection.status)}>
                      {detection.status}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted-foreground mb-2">{detection.label}</p>
                  <div className="flex items-center justify-between text-xs text-muted-foreground">
                    <span>Confidence: {detection.confidence.toFixed(1)}%</span>
                    <span>
                      Position: ({detection.boundingBox.x.toFixed(0)}, {detection.boundingBox.y.toFixed(0)})
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* No Detections State */}
        {(!produce.detections || produce.detections.length === 0) && (
          <div className="text-center py-8 bg-gray-50 rounded-lg">
            <ImageIcon className="h-12 w-12 mx-auto mb-3 text-gray-400" />
            <p className="text-sm font-medium mb-1">No ML Analysis Yet</p>
            <p className="text-xs text-muted-foreground mb-4">
              Click the refresh button to run quality detection
            </p>
            <Button onClick={handleRunAnalysis} disabled={isAnalyzing}>
              <RefreshCw className="h-4 w-4 mr-2" />
              Run ML Analysis
            </Button>
          </div>
        )}

        {/* ML Backend Connection Note */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-xs text-blue-800">
          <p className="font-medium mb-1">🤖 ML Backend Integration</p>
          <p>
            Connect your ML classification API endpoint to replace mock detections with real-time analysis.
            The app is structured to easily integrate with your backend via Supabase functions or direct API calls.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex gap-2">
          <Button 
            onClick={handleRunAnalysis}
            disabled={isAnalyzing}
            className="flex-1"
          >
            <RefreshCw className={`h-4 w-4 mr-2 ${isAnalyzing ? 'animate-spin' : ''}`} />
            {isAnalyzing ? 'Analyzing...' : 'Run Analysis'}
          </Button>
          <Button variant="outline" className="flex-1">
            <Download className="h-4 w-4 mr-2" />
            Export Report
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}