import { Card, CardContent, CardHeader, CardTitle } from "./ui/card";
import { Button } from "./ui/button";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { Input } from "./ui/input";
import { 
  List, 
  Search,
  Apple,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  Clock
} from "lucide-react";
import type { ProduceItem } from "../App";
import { useState } from "react";

interface ProduceListProps {
  items: ProduceItem[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ProduceList({ items, selectedId, onSelect }: ProduceListProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const [filterStatus, setFilterStatus] = useState<string>("all");

  const filteredItems = items.filter(item => {
    const matchesSearch = item.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
                         item.category.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = filterStatus === "all" || item.status === filterStatus;
    return matchesSearch && matchesStatus;
  });

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'good':
        return <CheckCircle2 className="h-4 w-4 text-green-600" />;
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-yellow-600" />;
      case 'bad':
        return <XCircle className="h-4 w-4 text-red-600" />;
      default:
        return <Clock className="h-4 w-4 text-gray-400" />;
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

  const getStatusText = (status: string) => {
    switch (status) {
      case 'good':
        return 'Good';
      case 'warning':
        return 'Warning';
      case 'bad':
        return 'Bad';
      case 'unchecked':
        return 'Unchecked';
      default:
        return 'Unknown';
    }
  };

  const formatTimeAgo = (date: Date) => {
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    
    const minutes = Math.floor(diff / (1000 * 60));
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));
    
    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  return (
    <Card className="h-full">
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          <List className="h-5 w-5" />
          Produce Items
          <Badge variant="secondary">{filteredItems.length}</Badge>
        </CardTitle>
      </CardHeader>
      
      <CardContent className="space-y-4">
        {/* Search */}
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
          <Input
            placeholder="Search produce..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="pl-9"
          />
        </div>

        {/* Status Filters */}
        <div className="flex gap-2 flex-wrap">
          <Button
            variant={filterStatus === "all" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterStatus("all")}
            className="text-xs"
          >
            All
          </Button>
          <Button
            variant={filterStatus === "good" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterStatus("good")}
            className="text-xs"
          >
            <CheckCircle2 className="h-3 w-3 mr-1" />
            Good
          </Button>
          <Button
            variant={filterStatus === "warning" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterStatus("warning")}
            className="text-xs"
          >
            <AlertTriangle className="h-3 w-3 mr-1" />
            Warning
          </Button>
          <Button
            variant={filterStatus === "bad" ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterStatus("bad")}
            className="text-xs"
          >
            <XCircle className="h-3 w-3 mr-1" />
            Bad
          </Button>
        </div>

        {/* Produce List */}
        <ScrollArea className="h-[calc(100vh-350px)]">
          <div className="space-y-2">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                className={`border rounded-lg p-3 cursor-pointer transition-all hover:shadow-md ${
                  selectedId === item.id 
                    ? 'ring-2 ring-green-500 bg-green-50 border-green-200' 
                    : 'hover:bg-gray-50'
                }`}
                onClick={() => onSelect(item.id)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2 flex-1">
                    {getStatusIcon(item.status)}
                    <div className="flex-1 min-w-0">
                      <h4 className="font-medium text-sm truncate">{item.name}</h4>
                      <p className="text-xs text-muted-foreground">{item.category}</p>
                    </div>
                  </div>
                  <Badge className={`${getStatusColor(item.status)} text-xs`}>
                    {getStatusText(item.status)}
                  </Badge>
                </div>

                <div className="space-y-1 text-xs text-muted-foreground">
                  <div className="flex justify-between">
                    <span>Quantity:</span>
                    <span className="font-medium text-gray-900">{item.quantity}</span>
                  </div>
                  {item.price && (
                    <div className="flex justify-between">
                      <span>Price:</span>
                      <span className="font-medium text-gray-900">${item.price.toFixed(2)}</span>
                    </div>
                  )}
                  {item.confidence > 0 && (
                    <div className="flex justify-between">
                      <span>Confidence:</span>
                      <span className="font-medium text-gray-900">{item.confidence.toFixed(0)}%</span>
                    </div>
                  )}
                  <div className="flex justify-between">
                    <span>Last Checked:</span>
                    <span className="font-medium text-gray-900">{formatTimeAgo(item.last_checked)}</span>
                  </div>
                  {item.supplier && (
                    <div className="flex justify-between">
                      <span>Supplier:</span>
                      <span className="font-medium text-gray-900 truncate max-w-[150px]" title={item.supplier}>
                        {item.supplier}
                      </span>
                    </div>
                  )}
                </div>

                {item.detections && item.detections.length > 0 && (
                  <div className="mt-2 pt-2 border-t border-gray-200">
                    <p className="text-xs text-muted-foreground">
                      {item.detections.length} detection{item.detections.length !== 1 ? 's' : ''}
                    </p>
                  </div>
                )}
              </div>
            ))}

            {filteredItems.length === 0 && (
              <div className="text-center py-8 text-muted-foreground">
                <Apple className="h-12 w-12 mx-auto mb-2 opacity-30" />
                <p className="text-sm">No produce items found</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </CardContent>
    </Card>
  );
}
