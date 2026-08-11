from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple

from src.evidence.evidence_knowledge import EVIDENCE_KNOWLEDGE
from src.evidence.evidence_object import EvidenceObject


class EvidenceSourceMappingError(ValueError):
    """Raised when curated source mapping data is invalid or ambiguous."""


@dataclass(frozen=True, slots=True)
class EvidenceSourceMapping:
    """Exact mapping from one source phrase to one or more Evidence Objects."""

    source_title: str
    evidence_ids: Tuple[str, ...]
    rationale: str = ""

    def __post_init__(self) -> None:
        source_title = self.source_title.strip()
        evidence_ids = tuple(
            dict.fromkeys(value.strip() for value in self.evidence_ids if value.strip())
        )

        if not source_title:
            raise EvidenceSourceMappingError("source_title cannot be blank.")
        if not evidence_ids:
            raise EvidenceSourceMappingError("evidence_ids cannot be empty.")

        object.__setattr__(self, "source_title", source_title)
        object.__setattr__(self, "evidence_ids", evidence_ids)
        object.__setattr__(self, "rationale", self.rationale.strip())


class EvidenceSourceMappingCatalog:
    """Case-insensitive exact lookup for curated, potentially compound mappings."""

    def __init__(
        self,
        mappings: Iterable[EvidenceSourceMapping] = (),
        *,
        evidence_objects: Iterable[EvidenceObject] = EVIDENCE_KNOWLEDGE,
    ) -> None:
        objects = tuple(evidence_objects)
        self._evidence_by_id: Dict[str, EvidenceObject] = {
            item.evidence_id.casefold(): item for item in objects
        }
        self._mappings: Dict[str, EvidenceSourceMapping] = {}

        for mapping in mappings:
            key = mapping.source_title.casefold()
            if key in self._mappings:
                raise EvidenceSourceMappingError(
                    f"Duplicate source mapping title: {mapping.source_title!r}."
                )
            unknown_ids = [
                evidence_id
                for evidence_id in mapping.evidence_ids
                if evidence_id.casefold() not in self._evidence_by_id
            ]
            if unknown_ids:
                raise EvidenceSourceMappingError(
                    f"Unknown Evidence Object IDs for {mapping.source_title!r}: "
                    f"{unknown_ids!r}."
                )
            self._mappings[key] = mapping

    def resolve(self, source_title: str) -> Tuple[EvidenceObject, ...]:
        mapping = self._mappings.get(str(source_title).strip().casefold())
        if mapping is None:
            return ()
        return tuple(
            self._evidence_by_id[evidence_id.casefold()]
            for evidence_id in mapping.evidence_ids
        )

    @property
    def mappings(self) -> Tuple[EvidenceSourceMapping, ...]:
        return tuple(
            sorted(
                self._mappings.values(), key=lambda item: item.source_title.casefold()
            )
        )


DEFAULT_EVIDENCE_SOURCE_MAPPINGS: Tuple[EvidenceSourceMapping, ...] = (
    EvidenceSourceMapping(
        "Audit Record Reduction Review Analysis and Reporting Tools",
        ("EV-0111", "EV-0105"),
        "The source combines audit-logging tools with broader security-analysis tools.",
    ),
    EvidenceSourceMapping(
        "Authenticator Feedback Procedures",
        ("EV-0017",),
        "The source is an authenticator-management procedure variant.",
    ),
    EvidenceSourceMapping(
        "Authorizations for Mobile Device Connections to Organizational Systems",
        ("EV-0013",),
        "The source requests records authorizing specific connections.",
    ),
    EvidenceSourceMapping(
        "Backup Storage Location S",
        ("EV-0048",),
        "Backup storage location is part of backup configuration; the trailing S is source noise.",
    ),
    EvidenceSourceMapping(
        "Boundary Protection Hardware and Software",
        ("EV-0021", "EV-0022", "EV-0035"),
        "The source combines boundary hardware, software, and firewall configuration evidence.",
    ),
    EvidenceSourceMapping(
        "Change Control Audit and Review Reports",
        ("EV-0030",),
        "The source is a configuration-review record variant.",
    ),
    EvidenceSourceMapping(
        "Change Control Records Associated with Managing System Authenticators",
        ("EV-0029",),
        "The source requests change-management records scoped to authenticators.",
    ),
    EvidenceSourceMapping(
        "Configuration Settings for the System Procedures",
        ("EV-0089",),
        "The source is a configuration-management procedure variant.",
    ),
    EvidenceSourceMapping(
        "Cryptographic Mechanisms",
        ("EV-0070",),
        "The source identifies the organization's implemented cryptographic mechanisms.",
    ),
    EvidenceSourceMapping(
        "Documented Reviews of Programs Functions Ports Protocols and or Services",
        ("EV-0027",),
        "The owner classified this source as evidence of the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "Evidence Supporting Approved Deviations from Established Configuration Settings",
        ("EV-0009",),
        "Approved deviations are tracked as exceptions.",
    ),
    EvidenceSourceMapping(
        "Identifier Management Procedures",
        ("EV-0127",),
        "The source is an identity and access management procedure variant.",
    ),
    EvidenceSourceMapping(
        "Incident Monitoring Procedures",
        ("EV-0042",),
        "The source is an incident-response procedure variant.",
    ),
    EvidenceSourceMapping(
        "Incident Reporting Procedures",
        ("EV-0042",),
        "The source is an incident-response procedure variant.",
    ),
    EvidenceSourceMapping(
        "Incident Response Assistance Procedures",
        ("EV-0042",),
        "The source is an incident-response procedure variant.",
    ),
    EvidenceSourceMapping(
        "Incident Response Test Results",
        ("EV-0044",),
        "Incident response test results are incident response exercise records.",
    ),
    EvidenceSourceMapping(
        "Incident Response Training Records",
        ("EV-0060",),
        "The source is a security-training record scoped to incident response.",
    ),
    EvidenceSourceMapping(
        "Insider Threat Policy and Procedures",
        ("EV-0136", "EV-0137"),
        "The source combines insider threat policy and procedure artifacts.",
    ),
    EvidenceSourceMapping(
        "Installation Change Control Records for Security Relevant Software and Firmware Updates",
        ("EV-0029", "EV-0078"),
        "The source combines change-control and patch-deployment records.",
    ),
    EvidenceSourceMapping(
        "Inventory Records of Physical Access Control Devices",
        ("EV-0021",),
        "Physical access control devices are represented in the hardware asset inventory.",
    ),
    EvidenceSourceMapping(
        "Inventory Review and Update Records",
        ("EV-0139", "EV-0021", "EV-0022", "EV-0023"),
        "The source combines asset inventory procedures with the inventories they maintain.",
    ),
    EvidenceSourceMapping(
        "Least Functionality in the System Procedures",
        ("EV-0089",),
        "Least-functionality activities are part of configuration management procedures.",
    ),
    EvidenceSourceMapping(
        "Least Privilege Procedures",
        ("EV-0127",),
        "Least-privilege activities are part of identity and access management procedures.",
    ),
    EvidenceSourceMapping(
        "List of Acceptable Mobile Code and Mobile Code Technologies",
        ("EV-0027",),
        "Approved mobile code and technologies are governed by the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "List of Active System Accounts and the Name of the Individual Associated with Each Account",
        ("EV-0011",),
        "The source is an account inventory variant.",
    ),
    EvidenceSourceMapping(
        "List of All Managed Network Access Control Points",
        ("EV-0021",),
        "Managed network access points are represented in the hardware asset inventory.",
    ),
    EvidenceSourceMapping(
        "List of Approved Authorizations User Privileges Including Remote Access Authorizations",
        ("EV-0013",),
        "The source is an access-authorization record variant.",
    ),
    EvidenceSourceMapping(
        "List of Conditions for Group and Role Membership",
        ("EV-0127",),
        "Group membership and RBAC criteria are part of identity and access management procedures.",
    ),
    EvidenceSourceMapping(
        "List of Conditions or Trigger Events Requiring Session Disconnect",
        ("EV-0127",),
        "Session timeout, lock, and disconnect criteria are part of identity and access management procedures.",
    ),
    EvidenceSourceMapping(
        "List of Devices and Other Systems Authorized to Connect to Organizational Systems",
        ("EV-0021",),
        "Authorized connected devices and systems are represented in the hardware asset inventory.",
    ),
    EvidenceSourceMapping(
        "List of Divisions of Responsibility and Separation of Duties",
        ("EV-0122",),
        "The source documents separation-of-duties assignments and responsibilities.",
    ),
    EvidenceSourceMapping(
        "List of Fips Validated Cryptographic Modules",
        ("EV-0118",),
        "The source is an inventory-oriented presentation of cryptographic module validation evidence.",
    ),
    EvidenceSourceMapping(
        "List of Flaws and Vulnerabilities Potentially Affecting the System",
        ("EV-0077",),
        "Identified system flaws and vulnerabilities are maintained as vulnerability management records.",
    ),
    EvidenceSourceMapping(
        "List of Identifiers Generated from Physical Access Control Devices",
        ("EV-0053",),
        "Identifiers generated by physical access control devices are represented in physical access logs.",
    ),
    EvidenceSourceMapping(
        "List of Information at Rest Requiring Confidentiality Protections",
        ("EV-0023",),
        "The information asset inventory identifies the data holdings and classification attributes that determine required protections.",
    ),
    EvidenceSourceMapping(
        "List of Information Flow Authorizations",
        ("EV-0135", "EV-0013"),
        "The source combines information-flow enforcement procedures with the corresponding access authorizations.",
    ),
    EvidenceSourceMapping(
        "List of Key Internal Boundaries of the System",
        ("EV-0031", "EV-0033"),
        "Internal boundaries are represented in network diagrams and system architecture documentation.",
    ),
    EvidenceSourceMapping(
        "List of Organization Defined Event Types to Be Logged",
        ("EV-0112",),
        "Organization-defined logged event types are specified by audit logging procedures.",
    ),
    EvidenceSourceMapping(
        "List of Personnel to Be Notified in Case of an Audit Logging Processing Failure",
        ("EV-0045",),
        "Notification recipients for logging failures are represented in incident communication records.",
    ),
    EvidenceSourceMapping(
        "List of Privileged Functions and Associated User Account Assignments",
        ("EV-0012", "EV-0013"),
        "The source combines privileged account inventory data with access authorization assignments.",
    ),
    EvidenceSourceMapping(
        "List of Privileged System Accounts",
        ("EV-0012",),
        "The source is a privileged account inventory variant.",
    ),
    EvidenceSourceMapping(
        "List of Recently Disabled System Accounts Along with the Name of the Individual Associated with Each Account",
        ("EV-0011", "EV-0102"),
        "The source combines account inventory status with account management review records.",
    ),
    EvidenceSourceMapping(
        "List of Rules Governing User Installed Software",
        ("EV-0027",),
        "Rules governing user-installed software are part of the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "List of Safeguards Required for Alternate Work Sites",
        ("EV-0104",),
        "The source specifies safeguards implemented through alternate work site security procedures.",
    ),
    EvidenceSourceMapping(
        "List of Security Functions Deployed in Hardware Software and Firmware and Security Relevant Information for Which Access Must Be Explicitly Authorized",
        ("EV-0027",),
        "Deployed security functions and their restricted settings are governed by the secure configuration and hardening standard.",
    ),
    EvidenceSourceMapping(
        "List of Security Safeguards Controlling Access to Designated Publicly Accessible Areas Within Facility",
        ("EV-0140",),
        "Public-area access safeguards are requirements within the physical security policy.",
    ),
    EvidenceSourceMapping(
        "List of Software Programs Authorized to Execute on the System",
        ("EV-0022", "EV-0027"),
        "The source combines the software inventory with secure configuration allowlisting requirements.",
    ),
    EvidenceSourceMapping(
        "List of Software Programs Not Authorized to Execute on the System",
        ("EV-0027",),
        "Prohibited-software and denylisting requirements are part of the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "List of System Administration Personnel",
        ("EV-0012",),
        "The source is a privileged administrative account inventory variant.",
    ),
    EvidenceSourceMapping(
        "List of System Authenticator Types",
        ("EV-0126",),
        "Permitted authenticator types and their requirements are governed by the identity and access management policy.",
    ),
    EvidenceSourceMapping(
        "List of System Generated Privileged Accounts",
        ("EV-0012",),
        "The source is a privileged account inventory variant.",
    ),
    EvidenceSourceMapping(
        "List of System Generated Security Functions Assigned to System Accounts or Roles",
        ("EV-0083",),
        "The source lists service-account or role permissions represented by the access control list.",
    ),
    EvidenceSourceMapping(
        "List of System Media Marking Security Attributes",
        ("EV-0023", "EV-0092"),
        "The source combines information classification attributes with media marking procedures.",
    ),
    EvidenceSourceMapping(
        "List of Types of Applications Accessible from External Systems",
        ("EV-0022", "EV-0019"),
        "The source combines the software inventory with remote access configuration.",
    ),
    EvidenceSourceMapping(
        "List of Unacceptable Mobile Code and Mobile Technologies",
        ("EV-0027",),
        "Prohibited mobile code and technologies are governed by the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "List of Users Authorized to Post Publicly Accessible Content on Organizational Systems",
        ("EV-0141",),
        "Authorized public-content publishers are maintained through public communications procedures.",
    ),
    EvidenceSourceMapping(
        "Locations Within System Where Monitoring Devices Are Deployed",
        ("EV-0021", "EV-0055"),
        "The source combines monitoring-device inventory and location data with physical security monitoring records.",
    ),
    EvidenceSourceMapping(
        "Maintenance Personnel Procedures",
        ("EV-0097", "EV-0086"),
        "The source combines maintenance procedures with the authorized personnel list.",
    ),
    EvidenceSourceMapping(
        "Manufacturer or Vendor Maintenance Specifications",
        ("EV-0097", "EV-0064"),
        "Vendor maintenance requirements inform internal maintenance procedures and applicable third-party agreements.",
    ),
    EvidenceSourceMapping(
        "Media Storage Facilities",
        ("EV-0093", "EV-0140"),
        "The media inventory identifies storage locations, while the physical security policy defines their required protection.",
    ),
    EvidenceSourceMapping(
        "Mobile Code Procedures",
        ("EV-0027",),
        "Mobile code approval, restriction, and implementation requirements are governed by the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "Mobile Code Usage Restrictions Mobile Code Implementation Policy and Procedures",
        ("EV-0027",),
        "Mobile code usage restrictions and implementation requirements are governed by the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "Network Disconnect Procedures",
        ("EV-0113",),
        "Network disconnection activities are part of boundary protection procedures.",
    ),
    EvidenceSourceMapping(
        "Organizational Procedures Addressing Security Plan Development and Implementation",
        ("EV-0001",),
        "Security plan development and implementation instructions are contained in the security plan.",
    ),
    EvidenceSourceMapping(
        "Organizational Risk Assessments Procedures",
        ("EV-0143",),
        "The source is a risk assessment procedure variant.",
    ),
    EvidenceSourceMapping(
        "Personnel Screening Procedures",
        ("EV-0144",),
        "Personnel screening requirements are maintained as a section of the human resources manual.",
    ),
    EvidenceSourceMapping(
        "Personnel Security Policy",
        ("EV-0144",),
        "Personnel security requirements are maintained as a section of the human resources manual.",
    ),
    EvidenceSourceMapping(
        "Personnel Transfer and Termination Procedures",
        ("EV-0144",),
        "Transfer and termination requirements are maintained as sections of the human resources manual.",
    ),
    EvidenceSourceMapping(
        "Physical Access Authorizations Procedures",
        ("EV-0082",),
        "Physical access authorization follows the unified access control procedures.",
    ),
    EvidenceSourceMapping(
        "Physical Access Control Devices",
        ("EV-0021",),
        "Physical access control devices are represented in the hardware asset inventory.",
    ),
    EvidenceSourceMapping(
        "Physical Access Control Procedures",
        ("EV-0082",),
        "Physical and logical access controls follow the unified access control procedures.",
    ),
    EvidenceSourceMapping(
        "Physical Access List Reviews",
        ("EV-0082",),
        "Physical access list review is part of the unified access control lifecycle.",
    ),
    EvidenceSourceMapping(
        "Physical Access Log Reviews",
        ("EV-0082", "EV-0053"),
        "Physical access log review follows the unified access control procedures and uses the physical access logs.",
    ),
    EvidenceSourceMapping(
        "Physical Access Monitoring Procedures",
        ("EV-0140",),
        "Physical access monitoring requirements are maintained within the physical security policy.",
    ),
    EvidenceSourceMapping(
        "Physical Access Termination Records and Associated Documentation",
        ("EV-0059", "EV-0052"),
        "The source combines personnel termination records with physical access authorization revocation evidence.",
    ),
    EvidenceSourceMapping(
        "Physical and Environmental Protection Policy and Procedures",
        ("EV-0140", "EV-0082"),
        "The source combines physical security policy requirements with unified access control procedures.",
    ),
    EvidenceSourceMapping(
        "Plan of Action",
        ("EV-0007",),
        "The source is a remediation action plan variant.",
    ),
    EvidenceSourceMapping(
        "Plan of Action Procedures",
        ("EV-0007",),
        "The remediation plan methodology and procedural instructions are contained in the remediation action plan.",
    ),
    EvidenceSourceMapping(
        "Privacy and Security Policies Procedures Addressing System Use Notification",
        ("EV-0123",),
        "System use notification requirements are governed by the system use banner policy.",
    ),
    EvidenceSourceMapping(
        "Protection of Audit Information Procedures",
        ("EV-0112",),
        "Protection of audit information is governed by audit logging procedures.",
    ),
    EvidenceSourceMapping(
        "Protection of Information at Rest Procedures",
        ("EV-0119", "EV-0092"),
        "The source combines cryptographic and media protection procedures for information at rest.",
    ),
    EvidenceSourceMapping(
        "Record of Actions Initiated by Malicious Code Protection Mechanisms in Response to Malicious Code Detection",
        ("EV-0043", "EV-0142"),
        "The source combines incident records with the malware protection procedures governing automated responses.",
    ),
    EvidenceSourceMapping(
        "Records of Exit Interviews",
        ("EV-0059", "EV-0144"),
        "Exit interview evidence is maintained with personnel termination records under the human resources manual.",
    ),
    EvidenceSourceMapping(
        "Records of Key and Lock Combination Changes",
        ("EV-0052",),
        "Physical key and lock combination changes are physical access authorization records.",
    ),
    EvidenceSourceMapping(
        "Records of Malicious Code Protection Updates",
        ("EV-0079", "EV-0078"),
        "The source combines malware protection configuration state with patch management update records.",
    ),
    EvidenceSourceMapping(
        "Records of Publicly Accessible Information Reviews",
        ("EV-0141",),
        "Public content review records are maintained through public communications procedures.",
    ),
    EvidenceSourceMapping(
        "Records of Response to Nonpublic Information on Public Websites",
        ("EV-0043", "EV-0141"),
        "The source combines incident response evidence with public communications correction and removal procedures.",
    ),
    EvidenceSourceMapping(
        "Records of Security Plan Reviews and Updates",
        ("EV-0001",),
        "Review history and revision evidence are retained with the security plan.",
    ),
    EvidenceSourceMapping(
        "Records of Terminated or Revoked Authenticators and Credentials",
        ("EV-0085", "EV-0017"),
        "The source combines credential inventory status with authenticator management procedures.",
    ),
    EvidenceSourceMapping(
        "Remote Access Authorizations",
        ("EV-0013",),
        "The source is an access authorization record scoped to remote access.",
    ),
    EvidenceSourceMapping(
        "Remote Access Implementation and Usage Including Restrictions Procedures",
        ("EV-0127", "EV-0019"),
        "The source combines identity and access management procedures with remote access configuration restrictions.",
    ),
    EvidenceSourceMapping(
        "Remote Access to the System Procedures",
        ("EV-0127",),
        "Remote access activities are governed by identity and access management procedures.",
    ),
    EvidenceSourceMapping(
        "Response to Audit Logging Processing Failures Procedures",
        ("EV-0112", "EV-0042"),
        "The source combines audit logging failure handling with incident response procedures.",
    ),
    EvidenceSourceMapping(
        "Review and Update Records Associated with List of Authorized or Unauthorized Software Programs",
        ("EV-0022", "EV-0027"),
        "The source combines software inventory maintenance with secure configuration allowlisting and denylisting requirements.",
    ),
    EvidenceSourceMapping(
        "Reviewed and Updated Records of Logged Event Types",
        ("EV-0112",),
        "Logged event type review and update activities are governed by audit logging procedures.",
    ),
    EvidenceSourceMapping(
        "Risk Assessment Policy",
        ("EV-0145",),
        "Risk assessment requirements are governed by the broader risk management policy.",
    ),
    EvidenceSourceMapping(
        "Risk Assessment Results",
        ("EV-0005",),
        "The source is a risk assessment results variant.",
    ),
    EvidenceSourceMapping(
        "Risk Assessment Reviews",
        ("EV-0005", "EV-0143"),
        "The source combines the risk assessment artifact with its governing review procedures.",
    ),
    EvidenceSourceMapping(
        "Risk Assessment Updates",
        ("EV-0005", "EV-0143"),
        "The source combines the risk assessment artifact with its governing update procedures.",
    ),
    EvidenceSourceMapping(
        "Scan Results from Malicious Code Protection Mechanisms",
        ("EV-0080", "EV-0079"),
        "The source combines security operations reporting with the malware protection configuration that produced the results.",
    ),
    EvidenceSourceMapping(
        "Security Alerts Advisories and Directives Procedures",
        ("EV-0075", "EV-0040"),
        "The source combines security operations procedures with the security alerts they govern.",
    ),
    EvidenceSourceMapping(
        "Security Assessment and Authorization Policy",
        ("EV-0002",),
        "Security assessment and authorization requirements are maintained within the enterprise security policy.",
    ),
    EvidenceSourceMapping(
        "Security Assessment Evidence",
        ("EV-0008",),
        "The source is a security assessment evidence variant.",
    ),
    EvidenceSourceMapping(
        "Security Assessment Planning Procedures",
        ("EV-0147",),
        "Security assessment planning is governed by the security assessment procedures.",
    ),
    EvidenceSourceMapping(
        "Security Configuration Checklists",
        ("EV-0027",),
        "Security configuration checklists implement the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "Security Impact Analysis for Changes to the System Procedures",
        ("EV-0089", "EV-0090"),
        "The source combines configuration management procedures with security impact analysis evidence.",
    ),
    EvidenceSourceMapping(
        "Security Plan Development and Implementation Procedures",
        ("EV-0001",),
        "Security plan development and implementation instructions are contained in the security plan.",
    ),
    EvidenceSourceMapping(
        "Security Plan Reviews and Updates Procedures",
        ("EV-0001",),
        "Security plan review and update instructions are contained in the security plan.",
    ),
    EvidenceSourceMapping(
        "Security Planning Policy",
        ("EV-0001",),
        "Security planning governance is consolidated in the security plan.",
    ),
    EvidenceSourceMapping(
        "Security Planning Policy and Procedures",
        ("EV-0001",),
        "Security planning policy and procedural guidance are consolidated in the security plan.",
    ),
    EvidenceSourceMapping(
        "Security Training Curriculum",
        ("EV-0149",),
        "Security training curriculum is maintained within the security awareness training procedures.",
    ),
    EvidenceSourceMapping(
        "Security Training Implementation Procedures",
        ("EV-0149",),
        "Security training implementation is governed by the security awareness training procedures.",
    ),
    EvidenceSourceMapping(
        "Security Training Materials",
        ("EV-0149",),
        "Security training materials are maintained within the security awareness training procedures.",
    ),
    EvidenceSourceMapping(
        "Service Level Agreements",
        ("EV-0064",),
        "Service level agreements are third-party agreements.",
    ),
    EvidenceSourceMapping(
        "Session Authenticity Procedures",
        ("EV-0127",),
        "Session authenticity is governed by identity and access management procedures.",
    ),
    EvidenceSourceMapping(
        "Session Lock Procedures",
        ("EV-0127",),
        "Session locking is governed by identity and access management procedures.",
    ),
    EvidenceSourceMapping(
        "Session Termination Procedures",
        ("EV-0127",),
        "Session termination is governed by identity and access management procedures.",
    ),
    EvidenceSourceMapping(
        "Specifications for Preventing Software Program Execution",
        ("EV-0027",),
        "Software execution prevention specifications are part of the secure configuration standard.",
    ),
    EvidenceSourceMapping(
        "Storage Locations for Physical Access Control Devices",
        ("EV-0021", "EV-0140"),
        "The source combines hardware inventory location data with physical security requirements.",
    ),
    EvidenceSourceMapping(
        "System and Communications Protection Policy",
        ("EV-0134",),
        "System and communications protection requirements are governed by the security architecture policy.",
    ),
    EvidenceSourceMapping(
        "System and Information Integrity Policy",
        ("EV-0002",),
        "This framework-family policy label is governed within the enterprise security policy.",
    ),
    EvidenceSourceMapping(
        "System Auditable Events",
        ("EV-0112",),
        "Auditable event definitions are governed by audit logging procedures.",
    ),
    EvidenceSourceMapping(
        "System Component Installation Records",
        ("EV-0029", "EV-0025"),
        "The source combines change management records with asset lifecycle installation records.",
    ),
    EvidenceSourceMapping(
        "System Component Removal Records",
        ("EV-0029", "EV-0025"),
        "The source combines change management records with asset lifecycle removal records.",
    ),
    EvidenceSourceMapping(
        "System Configuration Change Control Procedures",
        ("EV-0089",),
        "System configuration change control is governed by configuration management procedures.",
    ),
    EvidenceSourceMapping(
        "System Configuration Settings and Associated Documentation",
        ("EV-0026", "EV-0028"),
        "The source combines the approved configuration baseline with exported system configuration evidence.",
    ),
    EvidenceSourceMapping(
        "System Connection or Processing Agreements",
        ("EV-0064",),
        "System connection and processing agreements are third-party agreements.",
    ),
    EvidenceSourceMapping(
        "System Entry and Exit Points",
        ("EV-0031", "EV-0033"),
        "System entry and exit points are represented in network diagrams and system architecture documentation.",
    ),
    EvidenceSourceMapping(
        "System Events",
        ("EV-0036",),
        "The source is an audit log event variant.",
    ),
    EvidenceSourceMapping(
        "System Generated List of Privileged Users with Access to Management of Audit Logging Functionality",
        ("EV-0012", "EV-0083"),
        "The source combines privileged account inventory data with access permissions for audit logging administration.",
    ),
    EvidenceSourceMapping(
        "System Hardware and Software",
        ("EV-0021", "EV-0022"),
        "The source combines hardware and software asset inventories.",
    ),
    EvidenceSourceMapping(
        "System Inventory Procedures",
        ("EV-0139",),
        "System inventory activities are governed by asset management procedures.",
    ),
    EvidenceSourceMapping(
        "System Inventory Records",
        ("EV-0021", "EV-0022", "EV-0023"),
        "System inventory records comprise hardware, software, and information asset inventories.",
    ),
    EvidenceSourceMapping(
        "System Maintenance Tools Procedures",
        ("EV-0097", "EV-0099"),
        "The source combines maintenance procedures with the maintenance tool inventory.",
    ),
    EvidenceSourceMapping(
        "System Monitoring Audit Records",
        ("EV-0036", "EV-0080"),
        "The source combines audit logs with security operations monitoring reports.",
    ),
    EvidenceSourceMapping(
        "System Monitoring Records",
        ("EV-0080",),
        "System monitoring records are represented by security operations reports.",
    ),
    EvidenceSourceMapping(
        "System Monitoring Tools and Techniques Documentation",
        ("EV-0039", "EV-0105"),
        "The source combines security monitoring configuration with the security analysis tool inventory.",
    ),
    EvidenceSourceMapping(
        "System Monitoring Tools and Techniques Procedures",
        ("EV-0075",),
        "System monitoring tools and techniques are governed by security operations procedures.",
    ),
    EvidenceSourceMapping(
        "Access Control Records",
        ("EV-0013", "EV-0014"),
        "The broad source phrase includes authorization and periodic access-review records.",
    ),
    EvidenceSourceMapping(
        "Access Enforcement Procedures",
        ("EV-0082",),
        "The source is an access-control procedure variant.",
    ),
    EvidenceSourceMapping(
        "Access Control Policy and Procedures",
        ("EV-0081", "EV-0082"),
        "The source combines access control policy and procedure artifacts.",
    ),
    EvidenceSourceMapping(
        "Access Restrictions for Changes to the System Procedures",
        ("EV-0082", "EV-0089"),
        "The source combines access restrictions with configuration-change procedures.",
    ),
    EvidenceSourceMapping(
        "Account Management Documents",
        ("EV-0084",),
        "The source wording refers to account-management process documentation.",
    ),
    EvidenceSourceMapping(
        "Analysis Tools and Associated Outputs",
        ("EV-0105", "EV-0106"),
        "The source combines the analysis-tool inventory with resulting analysis outputs.",
    ),
    EvidenceSourceMapping(
        "Configuration Management Policy and Procedures",
        ("EV-0088", "EV-0089"),
        "The source combines configuration management policy and procedures.",
    ),
    EvidenceSourceMapping(
        "Cryptographic Mechanisms and Associated Configuration Documentation",
        ("EV-0070", "EV-0073"),
        "The source phrase requests both the mechanism inventory and its configuration.",
    ),
    EvidenceSourceMapping(
        "Encryption Mechanisms and Associated Configuration Documentation",
        ("EV-0070", "EV-0073"),
        "Encryption mechanism and configuration evidence are independently reusable.",
    ),
    EvidenceSourceMapping(
        "Notifications or Records of Recently Transferred Separated or Terminated Employees",
        ("EV-0058", "EV-0059"),
        "The source combines personnel transfer and termination records.",
    ),
    EvidenceSourceMapping(
        "Patch and Vulnerability Management Records",
        ("EV-0077", "EV-0078"),
        "Vulnerability remediation and patch deployment records can exist independently.",
    ),
    EvidenceSourceMapping(
        "Media Access Restrictions Procedures",
        ("EV-0092",),
        "The source is a media-protection procedure variant.",
    ),
    EvidenceSourceMapping(
        "Media Marking Procedures",
        ("EV-0092",),
        "The source is a media-protection procedure variant.",
    ),
    EvidenceSourceMapping(
        "Media Sanitization and Disposal Procedures",
        ("EV-0092",),
        "The source is a media-protection procedure variant.",
    ),
    EvidenceSourceMapping(
        "Media Storage Procedures",
        ("EV-0092",),
        "The source is a media-protection procedure variant.",
    ),
    EvidenceSourceMapping(
        "Media Transport Procedures",
        ("EV-0092",),
        "The source is a media-protection procedure variant.",
    ),
    EvidenceSourceMapping(
        "Media Usage Restrictions Procedures",
        ("EV-0092",),
        "The source is a media-protection procedure variant.",
    ),
    EvidenceSourceMapping(
        "Records of Personnel Transfer and Termination Actions",
        ("EV-0058", "EV-0059"),
        "The source combines personnel transfer and termination records.",
    ),
    EvidenceSourceMapping(
        "Security Plan System Design Documentation",
        ("EV-0001", "EV-0033"),
        "A security plan and system design documentation are distinct artifacts.",
    ),
    EvidenceSourceMapping(
        "System Architecture and Configuration Documentation",
        ("EV-0033", "EV-0028"),
        "Architecture documentation and actual configuration evidence are distinct.",
    ),
    EvidenceSourceMapping(
        "System Configuration Settings and Associated Documentation System Audit Logs and Records",
        ("EV-0028", "EV-0036"),
        "The source combines system configuration evidence with audit logs.",
    ),
    EvidenceSourceMapping(
        "Controlled System Maintenance Procedures",
        ("EV-0097",),
        "The source is a system-maintenance procedure variant.",
    ),
    EvidenceSourceMapping(
        "Nonlocal System Maintenance Procedures",
        ("EV-0097",),
        "The source is a system-maintenance procedure variant.",
    ),
    EvidenceSourceMapping(
        "System Maintenance Tools and Associated Documentation",
        ("EV-0099",),
        "The source identifies approved system-maintenance tools.",
    ),
    EvidenceSourceMapping(
        "System Maintenance Tools and Media Procedures",
        ("EV-0097", "EV-0092"),
        "The source combines maintenance and media-handling procedures.",
    ),
)


def default_evidence_source_mapping_catalog() -> EvidenceSourceMappingCatalog:
    return EvidenceSourceMappingCatalog(DEFAULT_EVIDENCE_SOURCE_MAPPINGS)
