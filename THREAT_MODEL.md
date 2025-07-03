# Threat Model: Computer Vision Inspection System

## System Overview

The Computer Vision Inspection System is an AI-powered application that automates file verification against predefined criteria using Large Language Models (LLMs) and computer vision. The system is built on AWS serverless architecture with a React frontend and FastAPI backend.

This is sample code and **NOT** intended to be deployed directly into your AWS account for production use without modification.

### Architecture Components

- **Frontend**: React web application served via CloudFront CDN
- **Authentication**: Amazon Cognito with user pools
- **API**: FastAPI application running on AWS Lambda via API Gateway
- **Storage**: Amazon S3 for file storage and static website hosting
- **Database**: Amazon DynamoDB for application data
- **AI/ML Services**: Amazon Bedrock (LLMs) and Amazon Rekognition (computer vision)
- **Security**: AWS WAF for web application protection
- **Configuration**: AWS Systems Manager Parameter Store
- **Secrets**: AWS Secrets Manager
- **Location Services**: Amazon Location Service
- **Monitoring**: CloudWatch for logging and monitoring

## Assets Identification

### Critical Assets
1. **User Data**: Personal information, authentication credentials
2. **Image Collections**: Uploaded files containing potentially sensitive visual data
3. **Verification Results**: AI analysis results and confidence scores
4. **LLM Configurations**: System prompts and model configurations
5. **API Keys**: Third-party service credentials (Tavily API)
6. **AWS Credentials**: Service roles and permissions
7. **Application Code**: Source code and business logic

### Data Classification
- **Highly Sensitive**: User credentials, API keys, AWS service credentials
- **Sensitive**: Image files, verification results, personal data
- **Internal**: Application configurations, system prompts
- **Public**: Static web assets, documentation

## Threat Analysis (STRIDE)

### Spoofing (Identity)

#### T1: User Identity Spoofing
- **Threat**: Attackers impersonate legitimate users to access the system
- **Attack Vectors**: 
  - Credential stuffing attacks
  - Phishing for user credentials
  - Session hijacking
- **Impact**: Unauthorized access to user data and system functionality
- **Likelihood**: Medium
- **Risk**: High

#### T2: Service Identity Spoofing
- **Threat**: Malicious services impersonate legitimate AWS services
- **Attack Vectors**: DNS spoofing, man-in-the-middle attacks
- **Impact**: Data interception, credential theft
- **Likelihood**: Low
- **Risk**: Medium

### Tampering (Integrity)

#### T3: Image File Tampering
- **Threat**: Malicious modification of uploaded images during transit or storage
- **Attack Vectors**: 
  - Man-in-the-middle attacks during upload
  - Direct S3 bucket manipulation
  - Malicious file uploads
- **Impact**: Compromised verification results, system integrity
- **Likelihood**: Medium
- **Risk**: High

#### T4: Database Tampering
- **Threat**: Unauthorized modification of DynamoDB data
- **Attack Vectors**: 
  - Privilege escalation
  - SQL injection (though DynamoDB is NoSQL)
  - Compromised service credentials
- **Impact**: Data corruption, false verification results
- **Likelihood**: Low
- **Risk**: High

#### T5: Configuration Tampering
- **Threat**: Malicious modification of system configurations or LLM prompts
- **Attack Vectors**: 
  - Compromised admin credentials
  - Parameter Store manipulation
  - Code injection in prompts
- **Impact**: System behavior modification, biased AI results
- **Likelihood**: Medium
- **Risk**: High

### Repudiation (Non-repudiation)

#### T6: Action Repudiation
- **Threat**: Users deny performing actions in the system
- **Attack Vectors**: Insufficient logging, log tampering
- **Impact**: Accountability issues, compliance violations
- **Likelihood**: Medium
- **Risk**: Medium

### Information Disclosure (Confidentiality)

#### T7: Sensitive Data Exposure
- **Threat**: Unauthorized access to sensitive images or verification results
- **Attack Vectors**: 
  - Misconfigured S3 bucket permissions
  - API endpoint exposure
  - CloudWatch log exposure
  - Insecure data transmission
- **Impact**: Privacy violations, competitive intelligence loss
- **Likelihood**: Medium
- **Risk**: High

#### T8: API Key Exposure
- **Threat**: Third-party API keys (Tavily) exposed in logs or configuration
- **Attack Vectors**: 
  - Hardcoded credentials
  - Insecure secret management
  - Log file exposure
- **Impact**: Unauthorized API usage, financial loss
- **Likelihood**: Medium
- **Risk**: Medium

#### T9: AI Model Prompt Injection
- **Threat**: Malicious prompts designed to extract sensitive information from LLMs
- **Attack Vectors**: 
  - Crafted image descriptions
  - Prompt injection in user inputs
  - Social engineering through images
- **Impact**: Information leakage, model behavior manipulation
- **Likelihood**: High
- **Risk**: Medium

### Denial of Service (Availability)

#### T10: Resource Exhaustion
- **Threat**: System unavailability due to resource consumption
- **Attack Vectors**: 
  - Large file uploads
  - Excessive API calls
  - Lambda timeout exploitation
  - DynamoDB throttling
- **Impact**: Service disruption, increased costs
- **Likelihood**: High
- **Risk**: Medium

#### T11: AI Service Abuse
- **Threat**: Excessive usage of Bedrock/Rekognition services
- **Attack Vectors**: 
  - Automated bulk processing
  - Cost amplification attacks
  - Rate limit exhaustion
- **Impact**: High AWS costs, service unavailability
- **Likelihood**: Medium
- **Risk**: High

### Elevation of Privilege (Authorization)

#### T12: Privilege Escalation
- **Threat**: Users gaining unauthorized access to administrative functions
- **Attack Vectors**: 
  - IAM role assumption vulnerabilities
  - API endpoint authorization bypass
  - Cognito group manipulation
- **Impact**: Full system compromise, data breach
- **Likelihood**: Low
- **Risk**: High

#### T13: Cross-Account Access
- **Threat**: Unauthorized access to AWS resources from external accounts
- **Attack Vectors**: 
  - Misconfigured resource policies
  - Cross-account role assumptions
  - Public resource exposure
- **Impact**: Data breach, resource hijacking
- **Likelihood**: Low
- **Risk**: High

## Risk Assessment Matrix

| Threat ID | Threat                    | Likelihood | Impact | Risk Level |
| --------- | ------------------------- | ---------- | ------ | ---------- |
| T1        | User Identity Spoofing    | Medium     | High   | High       |
| T2        | Service Identity Spoofing | Low        | Medium | Medium     |
| T3        | Image File Tampering      | Medium     | High   | High       |
| T4        | Database Tampering        | Low        | High   | High       |
| T5        | Configuration Tampering   | Medium     | High   | High       |
| T6        | Action Repudiation        | Medium     | Medium | Medium     |
| T7        | Sensitive Data Exposure   | Medium     | High   | High       |
| T8        | API Key Exposure          | Medium     | Medium | Medium     |
| T9        | AI Model Prompt Injection | High       | Medium | Medium     |
| T10       | Resource Exhaustion       | High       | Medium | Medium     |
| T11       | AI Service Abuse          | Medium     | High   | High       |
| T12       | Privilege Escalation      | Low        | High   | High       |
| T13       | Cross-Account Access      | Low        | High   | High       |

## Security Controls and Mitigations

### Authentication and Authorization

#### Implemented Controls
- **Amazon Cognito**: User authentication with email-based sign-in
- **MFA Support**: Optional multi-factor authentication
- **Password Policy**: Strong password requirements (8+ chars, uppercase, digits, symbols)
- **Self-signup Disabled**: Prevents unauthorized account creation
- **IAM Roles**: Least privilege access for AWS services

#### Recommended Enhancements
- **Mandatory MFA**: Require MFA for all users
- **Session Management**: Implement session timeout and rotation
- **API Rate Limiting**: Implement per-user API rate limits
- **Role-Based Access Control**: Implement granular permissions based on user roles

### Data Protection

#### Implemented Controls
- **HTTPS Encryption**: All data in transit encrypted via TLS
- **S3 Encryption**: Server-side encryption for stored files
- **Secrets Manager**: Secure storage for API keys
- **Parameter Store**: Secure configuration management

#### Recommended Enhancements
- **Client-Side Encryption**: Encrypt sensitive data before upload
- **Data Classification**: Implement data labeling and handling policies
- **Data Retention**: Implement automated data lifecycle management
- **Backup Encryption**: Ensure all backups are encrypted

### Network Security

#### Implemented Controls
- **AWS WAF**: Web application firewall protection
- **CloudFront**: CDN with DDoS protection
- **VPC Isolation**: Services isolated within AWS network
- **Geographic Restrictions**: Content delivery limited to Australia

#### Recommended Enhancements
- **Network Segmentation**: Implement VPC with private subnets
- **Security Groups**: Restrict network access between services
- **VPN/Private Endpoints**: Use VPC endpoints for AWS service communication
- **Network Monitoring**: Implement network traffic analysis

### Application Security

#### Implemented Controls
- **Input Validation**: FastAPI automatic request validation
- **CORS Configuration**: Controlled cross-origin resource sharing
- **Error Handling**: Structured error responses without sensitive data exposure

#### Recommended Enhancements
- **Content Security Policy**: Implement CSP headers
- **Security Headers**: Add HSTS, X-Frame-Options, X-Content-Type-Options
- **Input Sanitization**: Implement comprehensive input sanitization
- **Output Encoding**: Ensure proper output encoding to prevent XSS

### AI/ML Security

#### Implemented Controls
- **Prompt Management**: Configurable system prompts stored securely
- **Model Access Control**: Bedrock access through IAM roles

#### Recommended Enhancements
- **Prompt Injection Detection**: Implement prompt injection filtering
- **Model Output Validation**: Validate and sanitize AI responses
- **Usage Monitoring**: Monitor AI service usage for anomalies
- **Content Filtering**: Implement content filtering for uploaded images

### Monitoring and Logging

#### Implemented Controls
- **CloudWatch Logging**: Comprehensive application logging
- **DynamoDB Logging**: Audit trail for data operations
- **API Gateway Logging**: Request/response logging

#### Recommended Enhancements
- **Security Information and Event Management (SIEM)**: Centralized security monitoring
- **Anomaly Detection**: Automated detection of unusual patterns
- **Real-time Alerting**: Immediate notification of security events
- **Log Integrity**: Implement log tampering protection

### Incident Response

#### Recommended Controls
- **Incident Response Plan**: Documented procedures for security incidents
- **Automated Response**: Implement automated threat response
- **Forensic Capabilities**: Maintain audit trails for investigation
- **Communication Plan**: Stakeholder notification procedures

## Compliance Considerations

### Data Privacy
- **GDPR Compliance**: Implement data subject rights (access, deletion, portability)
- **Data Minimization**: Collect only necessary data
- **Consent Management**: Implement proper consent mechanisms
- **Privacy by Design**: Integrate privacy considerations into system design

### Industry Standards
- **ISO 27001**: Information security management system
- **SOC 2**: Service organization controls for security and availability
- **NIST Cybersecurity Framework**: Comprehensive security framework
- **AWS Well-Architected Security Pillar**: AWS security best practices

## Security Testing Recommendations

### Regular Security Assessments
1. **Penetration Testing**: Annual third-party security assessments
2. **Vulnerability Scanning**: Automated scanning of infrastructure and applications
3. **Code Security Review**: Static and dynamic application security testing
4. **AI Red Teaming**: Specific testing for AI/ML vulnerabilities

### Continuous Monitoring
1. **Security Metrics**: Track security KPIs and trends
2. **Threat Intelligence**: Monitor for emerging threats
3. **Configuration Drift**: Detect unauthorized configuration changes
4. **Access Reviews**: Regular review of user permissions and access

Regular security reviews and updates to this threat model should be conducted as the system evolves and new threats emerge.