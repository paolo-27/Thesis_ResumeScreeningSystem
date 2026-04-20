import os
import resend

def send_applicant_status_email(email: str, name: str, status: str, job_title: str, match_percentage: int = None, details: str = None):
    # Set the Resend API key
    resend.api_key = os.getenv("VERIDIAN_RESEND_API_KEY")

    if not resend.api_key:
        print("Resend API key is missing. Email skipped.")
        return

    if status == "success":
        subject = f"Your application for {job_title} has been processed"
        html_content = f"""
        <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
            <h2>Application Update from Veridian</h2>
            <p>Hi {name},</p>
            <p>Your resume for the position of <strong>{job_title}</strong> has been successfully processed by our screening system.</p>
            <p><strong>Match Percentage:</strong> {match_percentage}%</p>
            <p>Our HR team will review your resume for shortlisting. We will be in touch with you regarding the next steps.</p>
            <p>Best regards,<br/>The Veridian Team</p>
        </div>
        """
    else:
        subject = f"Action Required: Issue processing your resume for {job_title}"
        html_content = f"""
         <div style="font-family: sans-serif; max-width: 600px; margin: 0 auto; color: #333;">
            <h2>Application Update from Veridian</h2>
            <p>Hi {name},</p>
            <p>We encountered an error while trying to process your resume for the position of <strong>{job_title}</strong>.</p>
            <p><strong>Status:</strong> Error / Formatting Issue</p>
            <p><strong>Details:</strong> {details or "We couldn't read your DOCX/PDF properly."}</p>
            <p>Please review your file and re-upload your resume at your earliest convenience.</p>
            <p>Best regards,<br/>The Veridian Team</p>
        </div>
        """
        
    try:
        response = resend.Emails.send({
            "from": "Veridian <onboarding@resend.dev>",
            "to": email,
            "subject": subject,
            "html": html_content
        })
        print(f"Email sent successfully to {email}: {response}")
    except Exception as e:
        print(f"Failed to send email to {email}: {str(e)}")
