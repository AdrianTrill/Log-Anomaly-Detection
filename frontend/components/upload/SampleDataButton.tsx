"use client";

import { Database } from "lucide-react";
import { Button } from "@/components/ui/button";

const SAMPLE_LOG_CONTENT = `2026-03-09 10:00:01 INFO api-gateway Application started on port 8080
2026-03-09 10:00:02 INFO api-gateway Health check endpoint registered
2026-03-09 10:00:03 DEBUG db-connector Establishing connection pool with max_size=20
2026-03-09 10:00:05 WARN config-loader Configuration file not found, using defaults
2026-03-09 10:00:10 INFO api-gateway Incoming request: GET /api/users from 192.168.1.100
2026-03-09 10:00:11 DEBUG auth-service Validating token for user_id=78234
2026-03-09 10:00:12 INFO auth-service Token valid for user_id=78234 role=admin
2026-03-09 10:00:15 INFO api-gateway Incoming request: POST /api/orders from 10.0.0.55
2026-03-09 10:00:16 DEBUG order-service Processing order payload size=2048 bytes
2026-03-09 10:00:17 INFO order-service Order created: order_id=a1b2c3d4-e5f6-7890-abcd-ef1234567890
2026-03-09 10:00:20 WARN db-connector Connection pool usage at 85% (17/20)
2026-03-09 10:00:22 ERROR payment-service Payment gateway timeout after 30000ms for txn=99281347
2026-03-09 10:00:23 ERROR payment-service Retry attempt 1/3 for transaction_id=99281347
2026-03-09 10:00:25 WARN payment-service Retry attempt 2/3 for transaction_id=99281347
2026-03-09 10:00:28 INFO payment-service Transaction 99281347 completed on retry
[2026-03-09 10:01:00] [INFO] [scheduler] Cron job batch-report started
[2026-03-09 10:01:05] [DEBUG] [scheduler] Processing 1500 records for batch
[2026-03-09 10:01:10] [INFO] [scheduler] Batch processing completed in 10200ms
[2026-03-09 10:01:12] [WARN] [scheduler] Next scheduled run exceeds recommended interval
[2026-03-09 10:02:00] [ERROR] [db-connector] Deadlock detected on table orders
[2026-03-09 10:02:01] [INFO] [db-connector] Deadlock resolved after 1 retry
STARTUP: All services initialized successfully
System health check passed - all 12 services responding
WARNING: Disk usage on /var/log at 91%
2026-03-09 10:03:00 INFO api-gateway Incoming request: DELETE /api/sessions from 10.0.0.1
2026-03-09 10:03:05 ERROR notification-service Failed to connect to SMTP server at 10.0.0.99:587
2026-03-09 10:03:06 ERROR notification-service Email delivery queue backed up: 47 pending messages
2026-03-09 10:04:00 INFO cache-service Cache miss for key=product_catalog fetching from DB
2026-03-09 10:04:05 WARN product-service 15 products have missing images
[2026-03-09 10:05:00] [INFO] [load-balancer] Traffic routing: 40% node-01, 35% node-02, 25% node-03
[2026-03-09 10:05:05] [WARN] [load-balancer] Node node-03 response time elevated: avg 450ms`;

interface SampleDataButtonProps {
  onFileSelect: (file: File) => void;
  disabled: boolean;
}

export function SampleDataButton({ onFileSelect, disabled }: SampleDataButtonProps) {
  const handleClick = () => {
    const blob = new Blob([SAMPLE_LOG_CONTENT], { type: "text/plain" });
    const file = new File([blob], "sample-demo.log", { type: "text/plain" });
    onFileSelect(file);
  };

  return (
    <Button variant="outline" size="sm" onClick={handleClick} disabled={disabled} className="gap-1.5 text-xs h-8">
      <Database className="h-3.5 w-3.5" />
      Load Sample Data
    </Button>
  );
}
