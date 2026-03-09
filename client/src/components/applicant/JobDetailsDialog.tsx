import { useState } from "react";
import api from "../../lib/axios";
import {
  MapPin,
  Building2,
  Coins,
  CheckCircle2,
  Upload,
  FileText,
} from "lucide-react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { Checkbox } from "../ui/checkbox";
import { Badge } from "../ui/badge";
import { ScrollArea } from "../ui/scroll-area";
import {
  AlertDialog,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";

interface JobDetailsDialogProps {
  job: {
    id: string;
    title: string;
    company: string;
    location: string;
    type: string;
    salary: string;
    description: string;
    requirements: string[];
    responsibilities: string[];
  } | null;
  open: boolean;
  onOpenChange: (open: boolean) => void;
}

export function JobDetailsDialog({
  job,
  open,
  onOpenChange,
}: JobDetailsDialogProps) {
  const [showApplication, setShowApplication] = useState(false);
  const [formData, setFormData] = useState({
    fullName: "",
    email: "",
    phoneNumber: "",
    resume: null as File | null,
    termsAccepted: false,
  });
  const [showConfirmation, setShowConfirmation] =
    useState(false);
  const [errors, setErrors] = useState<Record<string, string>>(
    {},
  );

  const handleFileChange = (
    e: React.ChangeEvent<HTMLInputElement>,
  ) => {
    if (e.target.files && e.target.files[0]) {
      setFormData({ ...formData, resume: e.target.files[0] });
      setErrors({ ...errors, resume: "" });
    }
  };

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.fullName.trim()) {
      newErrors.fullName = "Full name is required";
    }

    if (!formData.email.trim()) {
      newErrors.email = "Email is required";
    } else if (
      !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)
    ) {
      newErrors.email = "Please enter a valid email address";
    }

    if (!formData.phoneNumber.trim()) {
      newErrors.phoneNumber = "Phone number is required";
    } else if (!/^\+?[\d\s-()]+$/.test(formData.phoneNumber)) {
      newErrors.phoneNumber =
        "Please enter a valid phone number";
    }

    if (!formData.resume) {
      newErrors.resume = "Please upload your resume";
    }

    if (!formData.termsAccepted) {
      newErrors.terms =
        "You must accept the terms and conditions";
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (validateForm() && job) {
      try {
        const submissionData = new FormData();
        submissionData.append("name", formData.fullName);
        submissionData.append("email", formData.email);
        submissionData.append("phone", formData.phoneNumber);
        submissionData.append("jobId", job.id);
        if (formData.resume) {
          submissionData.append("resume", formData.resume);
        }

        await api.post("/api/apply", submissionData, {
          headers: {
            "Content-Type": "multipart/form-data",
          },
        });

        console.log("Application submitted to backend:", formData);
        setShowConfirmation(true);

        // Reset form
        setFormData({
          fullName: "",
          email: "",
          phoneNumber: "",
          resume: null,
          termsAccepted: false,
        });
        setShowApplication(false);
      } catch (error) {
        console.error("Failed to submit application", error);
        // Fallback for user experience, though minimal
        alert("There was an error submitting your application. Please try again.");
      }
    }
  };

  const handleDialogClose = () => {
    setShowApplication(false);
    setFormData({
      fullName: "",
      email: "",
      phoneNumber: "",
      resume: null,
      termsAccepted: false,
    });
    setErrors({});
    onOpenChange(false);
  };

  const handleConfirmationClose = () => {
    setShowConfirmation(false);
    handleDialogClose();
  };

  if (!job) return null;

  return (
    <>
      <Dialog open={open} onOpenChange={handleDialogClose}>
        <DialogContent className="max-w-4xl max-h-[90vh] p-0">
          <ScrollArea className="max-h-[90vh]">
            <div className="p-6">
              <DialogHeader>
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <DialogTitle className="text-2xl text-emerald-700 mb-2">
                      {job.title}
                    </DialogTitle>
                    <DialogDescription className="space-y-2">
                      <div className="flex items-center gap-2 text-gray-600">
                        <Building2 className="w-4 h-4" />
                        <span>{job.company}</span>
                      </div>
                      <div className="flex items-center gap-2 text-gray-600">
                        <MapPin className="w-4 h-4" />
                        <span>{job.location}</span>
                      </div>
                      <div className="flex items-center gap-2 text-gray-600">
                        <Coins className="w-4 h-4" />
                        <span>{job.salary}</span>
                      </div>
                      <div>
                        <Badge className="bg-emerald-100 text-emerald-700">
                          {job.type}
                        </Badge>
                      </div>
                    </DialogDescription>
                  </div>
                </div>
              </DialogHeader>

              {!showApplication ? (
                <div className="mt-6 space-y-6">
                  {/* Job Description */}
                  <div>
                    <h3 className="text-emerald-700 mb-2">
                      About the Role
                    </h3>
                    <p className="text-gray-600 leading-relaxed">
                      {job.description}
                    </p>
                  </div>

                  {/* Requirements */}
                  <div>
                    <h3 className="text-emerald-700 mb-3">
                      Requirements
                    </h3>
                    <ul className="space-y-2">
                      {job.requirements.map((req, index) => (
                        <li
                          key={index}
                          className="flex gap-2 text-gray-600"
                        >
                          <span className="text-emerald-600 mt-1">
                            •
                          </span>
                          <span>{req}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  {/* Responsibilities */}
                  <div>
                    <h3 className="text-emerald-700 mb-3">
                      Responsibilities
                    </h3>
                    <ul className="space-y-2">
                      {job.responsibilities.map(
                        (resp, index) => (
                          <li
                            key={index}
                            className="flex gap-2 text-gray-600"
                          >
                            <span className="text-emerald-600 mt-1">
                              •
                            </span>
                            <span>{resp}</span>
                          </li>
                        ),
                      )}
                    </ul>
                  </div>

                  <div className="pt-4 border-t">
                    <Button
                      onClick={() => setShowApplication(true)}
                      className="w-full bg-emerald-600 hover:bg-emerald-700"
                    >
                      Apply for this Position
                    </Button>
                  </div>
                </div>
              ) : (
                <form
                  onSubmit={handleSubmit}
                  className="mt-6 space-y-6"
                >
                  <div className="bg-emerald-50 p-4 rounded-lg border border-emerald-200">
                    <h3 className="text-emerald-700 mb-1">
                      Application Form
                    </h3>
                    <p className="text-sm text-gray-600">
                      Fill in your details to apply for{" "}
                      {job.title}
                    </p>
                  </div>

                  {/* Full Name */}
                  <div className="space-y-2">
                    <Label htmlFor="fullName">
                      Full Name{" "}
                      <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="fullName"
                      value={formData.fullName}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          fullName: e.target.value,
                        });
                        setErrors({ ...errors, fullName: "" });
                      }}
                      placeholder="Enter your full name"
                      className={
                        errors.fullName
                          ? "border-red-500"
                          : "border-emerald-200 focus:border-emerald-500"
                      }
                    />
                    {errors.fullName && (
                      <p className="text-sm text-red-500">
                        {errors.fullName}
                      </p>
                    )}
                  </div>

                  {/* Email */}
                  <div className="space-y-2">
                    <Label htmlFor="email">
                      Email Address{" "}
                      <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="email"
                      type="email"
                      value={formData.email}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          email: e.target.value,
                        });
                        setErrors({ ...errors, email: "" });
                      }}
                      placeholder="your.email@example.com"
                      className={
                        errors.email
                          ? "border-red-500"
                          : "border-emerald-200 focus:border-emerald-500"
                      }
                    />
                    {errors.email && (
                      <p className="text-sm text-red-500">
                        {errors.email}
                      </p>
                    )}
                  </div>

                  {/* Phone Number */}
                  <div className="space-y-2">
                    <Label htmlFor="phoneNumber">
                      Phone Number{" "}
                      <span className="text-red-500">*</span>
                    </Label>
                    <Input
                      id="phoneNumber"
                      type="tel"
                      value={formData.phoneNumber}
                      onChange={(e) => {
                        setFormData({
                          ...formData,
                          phoneNumber: e.target.value,
                        });
                        setErrors({
                          ...errors,
                          phoneNumber: "",
                        });
                      }}
                      placeholder="+63(XXX)XXX-XXXX"
                      className={
                        errors.phoneNumber
                          ? "border-red-500"
                          : "border-emerald-200 focus:border-emerald-500"
                      }
                    />
                    {errors.phoneNumber && (
                      <p className="text-sm text-red-500">
                        {errors.phoneNumber}
                      </p>
                    )}
                  </div>

                  {/* Resume Upload */}
                  <div className="space-y-2">
                    <Label htmlFor="resume">
                      Upload Resume{" "}
                      <span className="text-red-500">*</span>
                    </Label>
                    <div className="flex flex-col gap-2">
                      <div className="relative">
                        <input
                          id="resume"
                          type="file"
                          accept=".pdf,.docx"
                          onChange={handleFileChange}
                          className="hidden"
                        />
                        <label
                          htmlFor="resume"
                          className={`flex items-center justify-center gap-2 w-full px-4 py-3 border-2 border-dashed rounded-lg cursor-pointer transition-colors ${errors.resume
                            ? "border-red-500 bg-red-50"
                            : "border-emerald-300 bg-emerald-50 hover:bg-emerald-100"
                            }`}
                        >
                          <Upload className="w-5 h-5 text-emerald-600" />
                          <span className="text-sm text-gray-600">
                            {formData.resume
                              ? formData.resume.name
                              : "Click to upload resume (PDF, DOCX)"}
                          </span>
                        </label>
                      </div>
                      {formData.resume && (
                        <div className="flex items-center gap-2 text-sm text-emerald-700 bg-emerald-50 p-2 rounded">
                          <FileText className="w-4 h-4" />
                          <span>{formData.resume.name}</span>
                        </div>
                      )}
                      {errors.resume && (
                        <p className="text-sm text-red-500">
                          {errors.resume}
                        </p>
                      )}
                    </div>
                  </div>

                  {/* Terms and Conditions */}
                  <div className="space-y-2">
                    <div className="flex items-start gap-3 p-4 bg-gray-50 rounded-lg">
                      <Checkbox
                        id="terms"
                        checked={formData.termsAccepted}
                        onCheckedChange={(checked) => {
                          setFormData({
                            ...formData,
                            termsAccepted: checked as boolean,
                          });
                          setErrors({ ...errors, terms: "" });
                        }}
                        className="mt-1"
                      />
                      <div className="flex-1">
                        <Label
                          htmlFor="terms"
                          className="cursor-pointer"
                        >
                          I agree to the terms and conditions{" "}
                          <span className="text-red-500">
                            *
                          </span>
                        </Label>
                        <p className="text-xs text-gray-500 mt-1">
                          By submitting this application, you
                          agree to our data processing practices
                          and confirm that all information
                          provided is accurate and truthful.
                        </p>
                      </div>
                    </div>
                    {errors.terms && (
                      <p className="text-sm text-red-500">
                        {errors.terms}
                      </p>
                    )}
                  </div>

                  {/* Buttons */}
                  <div className="flex gap-3 pt-4 border-t">
                    <Button
                      type="button"
                      variant="outline"
                      onClick={() => {
                        setShowApplication(false);
                        setErrors({});
                      }}
                      className="flex-1 border-emerald-600 text-emerald-700 hover:bg-emerald-50"
                    >
                      Back to Job Details
                    </Button>
                    <Button
                      type="submit"
                      className="flex-1 bg-emerald-600 hover:bg-emerald-700"
                    >
                      Submit Application
                    </Button>
                  </div>
                </form>
              )}
            </div>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Confirmation Dialog */}
      <AlertDialog
        open={showConfirmation}
        onOpenChange={handleConfirmationClose}
      >
        <AlertDialogContent className="max-w-md">
          <AlertDialogHeader>
            <div className="flex justify-center mb-4">
              <div className="w-16 h-16 bg-emerald-100 rounded-full flex items-center justify-center">
                <CheckCircle2 className="w-10 h-10 text-emerald-600" />
              </div>
            </div>
            <AlertDialogTitle className="text-center text-2xl">
              Application Submitted Successfully!
            </AlertDialogTitle>
            <AlertDialogDescription className="text-center space-y-3">
              <p>
                Thank you for applying for the{" "}
                <span className="text-emerald-700">
                  {job.title}
                </span>{" "}
                position at{" "}
                <span className="text-emerald-700">
                  {job.company}
                </span>
                .
              </p>
              <p>
                We have received your application and our
                AI-powered resume screening system will analyze
                your qualifications. You will receive an email
                confirmation shortly.
              </p>
              <p className="text-sm text-gray-500">
                Our team will review your application and
                contact you if your profile matches our
                requirements.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="flex justify-center mt-4">
            <Button
              onClick={handleConfirmationClose}
              className="bg-emerald-600 hover:bg-emerald-700"
            >
              Close
            </Button>
          </div>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}