import React, { useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Badge } from '@/components/ui/badge';
import { Upload, Mail, ExternalLink, FileText, AlertCircle } from 'lucide-react';

interface ClioPlusWarRoomProps {
  caseId: string;
  jurisdiction: string;
  courtPortalUrl?: string;
}

export function ClioPlusWarRoom({ caseId, jurisdiction, courtPortalUrl }: ClioPlusWarRoomProps) {
  const [isUploading, setIsUploading] = useState(false);
  const [isSendingMail, setIsSendingMail] = useState(false);

  const handleMessyDocUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    
    setIsUploading(true);
    // Simulate upload to Messy-Doc Ingestion Engine
    setTimeout(() => {
      setIsUploading(false);
      alert('Documents uploaded and sent to Messy-Doc Ingestion Engine for OCR and context mapping.');
    }, 2000);
  };

  const handleSendCertifiedMail = async () => {
    setIsSendingMail(true);
    // Simulate API call to Certified Mail Integration (Lob)
    setTimeout(() => {
      setIsSendingMail(false);
      alert('Certified mail request sent via Lob API. Tracking number will be updated shortly.');
    }, 1500);
  };

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-6">
      {/* Messy-Doc Ingestion */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center">
            <Upload className="w-5 h-5 mr-2 text-blue-500" />
            Messy-Doc Ingestion
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 mb-4">
            Upload blurry faxes, handwritten notes, or email threads. Our engine will OCR, thread, and extract legal facts automatically.
          </p>
          <div className="flex items-center justify-center w-full">
            <label className="flex flex-col items-center justify-center w-full h-32 border-2 border-dashed rounded-lg cursor-pointer hover:bg-gray-50 border-gray-300">
              <div className="flex flex-col items-center justify-center pt-5 pb-6">
                <FileText className="w-8 h-8 mb-3 text-gray-400" />
                <p className="mb-2 text-sm text-gray-500">
                  <span className="font-semibold">Click to upload</span> or drag and drop
                </p>
              </div>
              <Input 
                type="file" 
                className="hidden" 
                multiple 
                onChange={handleMessyDocUpload}
                disabled={isUploading}
              />
            </label>
          </div>
          {isUploading && <p className="text-sm text-blue-500 mt-2 text-center">Processing documents...</p>}
        </CardContent>
      </Card>

      {/* Court Portal Integration */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center">
            <ExternalLink className="w-5 h-5 mr-2 text-green-500" />
            Court Portal Access
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 mb-4">
            Direct integration with {jurisdiction} e-filing systems (PACER/Tyler Odyssey).
          </p>
          <div className="space-y-3">
            <div className="flex justify-between items-center p-3 bg-gray-50 rounded-md border">
              <span className="text-sm font-medium">CourtListener Monitor</span>
              <Badge variant="outline" className="bg-green-50 text-green-700 border-green-200">Active</Badge>
            </div>
            <Button 
              className="w-full" 
              variant="outline"
              onClick={() => window.open(courtPortalUrl || 'https://pacer.uscourts.gov', '_blank')}
            >
              Open Court Portal
              <ExternalLink className="w-4 h-4 ml-2" />
            </Button>
            <Button className="w-full bg-green-600 hover:bg-green-700 text-white">
              Auto-File Approved Docs
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Certified Mail API */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-lg flex items-center">
            <Mail className="w-5 h-5 mr-2 text-purple-500" />
            Service of Process
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-gray-500 mb-4">
            Send physical documents via USPS Certified Mail with Return Receipt.
          </p>
          <div className="space-y-3">
            <div className="flex items-start p-3 bg-amber-50 rounded-md border border-amber-200">
              <AlertCircle className="w-5 h-5 text-amber-500 mr-2 mt-0.5 flex-shrink-0" />
              <div className="text-sm text-amber-800">
                <strong>Action Required:</strong> Complaint must be served to opposing party within 14 days.
              </div>
            </div>
            <Button 
              className="w-full bg-purple-600 hover:bg-purple-700 text-white"
              onClick={handleSendCertifiedMail}
              disabled={isSendingMail}
            >
              {isSendingMail ? 'Sending...' : 'Send via Certified Mail'}
              {!isSendingMail && <Mail className="w-4 h-4 ml-2" />}
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
