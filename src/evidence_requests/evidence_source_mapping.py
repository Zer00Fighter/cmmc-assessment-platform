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
