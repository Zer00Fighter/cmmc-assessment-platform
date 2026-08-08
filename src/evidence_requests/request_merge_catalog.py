from __future__ import annotations

from typing import Tuple

from src.evidence_requests.drl_model import DocumentationRequestType
from src.evidence_requests.request_optimizer import RequestMergeRule


DEFAULT_REQUEST_MERGE_RULES: Tuple[RequestMergeRule, ...] = (
    RequestMergeRule(
        package_title="Access Control Policy and Procedures",
        source_titles=(
            "Access Control Policy",
            "Access Control Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Access Control policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Audit and Accountability Policy and Procedures",
        source_titles=(
            "Audit and Accountability Policy",
            "Audit and Accountability Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Audit and Accountability policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Configuration Management Policy and Procedures",
        source_titles=(
            "Configuration Management Policy",
            "Configuration Management Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Configuration Management policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Identification and Authentication Policy and Procedures",
        source_titles=(
            "Identification and Authentication Policy",
            "Identification and Authentication Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Identification and Authentication policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Incident Response Policy and Procedures",
        source_titles=(
            "Incident Response Policy",
            "Incident Response Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Incident Response policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Maintenance Policy and Procedures",
        source_titles=(
            "System Maintenance Policy",
            "Maintenance Policy",
            "Maintenance Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current maintenance policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Media Protection Policy and Procedures",
        source_titles=(
            "System Media Protection Policy",
            "Media Protection Policy",
            "Media Protection Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Media Protection policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Personnel Security Policy and Procedures",
        source_titles=(
            "Personnel Security Policy",
            "Personnel Security Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Personnel Security policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Physical Protection Policy and Procedures",
        source_titles=(
            "Physical and Environmental Protection Policy",
            "Physical Protection Policy",
            "Physical Protection Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Physical Protection policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Risk Assessment Policy and Procedures",
        source_titles=(
            "Risk Assessment Policy",
            "Risk Assessment Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Risk Assessment policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="Security Assessment Policy and Procedures",
        source_titles=(
            "Security Assessment Policy",
            "Security Assessment Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current Security Assessment policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="System and Communications Protection Policy and Procedures",
        source_titles=(
            "System and Communications Protection Policy",
            "System and Communications Protection Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current System and Communications Protection policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="System and Information Integrity Policy and Procedures",
        source_titles=(
            "System and Information Integrity Policy",
            "System and Information Integrity Policy and Procedures",
        ),
        evidence_type=DocumentationRequestType.POLICY,
        description=(
            "Provide the current System and Information Integrity policy and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="System and Privileged Account Inventory",
        source_titles=(
            "List of System Accounts",
            "Privileged Account List",
            "Service Account List",
            "Shared Account List",
        ),
        evidence_type=DocumentationRequestType.INVENTORY,
        description=(
            "Provide the current inventory of system, privileged, service, and shared accounts."
        ),
    ),
    RequestMergeRule(
        package_title="Account Management Documentation",
        source_titles=(
            "Account Management Procedures",
            "Account Management Process",
            "Account Management Records",
        ),
        evidence_type=DocumentationRequestType.PROCEDURE,
        description=(
            "Provide account management procedures, process documentation, and associated records."
        ),
    ),
    RequestMergeRule(
        package_title="System Configuration Baseline and Settings",
        source_titles=(
            "Configuration Baseline",
            "System Configuration Baseline",
            "System Configuration Settings and Associated Documentation",
            "Security Configuration Settings",
        ),
        evidence_type=DocumentationRequestType.CONFIGURATION_BASELINE,
        description=(
            "Provide the approved configuration baseline, current system configuration settings, and supporting documentation."
        ),
    ),
    RequestMergeRule(
        package_title="Change Management Records",
        source_titles=(
            "Change Control Records",
            "Configuration Change Control Records",
            "Change Management Records",
        ),
        evidence_type=DocumentationRequestType.RECORD,
        description=(
            "Provide configuration and change management records demonstrating approved and tracked changes."
        ),
    ),
    RequestMergeRule(
        package_title="System Audit Logs and Records",
        source_titles=(
            "System Audit Logs and Records",
            "Audit Logs",
            "Audit Records",
            "Security Audit Logs",
            "System Logs",
        ),
        evidence_type=DocumentationRequestType.LOG,
        description=(
            "Provide representative system audit logs, security logs, and associated audit records."
        ),
    ),
    RequestMergeRule(
        package_title="System Security Plan",
        source_titles=(
            "Security Plan",
            "System Security Plan",
        ),
        evidence_type=DocumentationRequestType.SYSTEM_SECURITY_PLAN,
        description=(
            "Provide the current System Security Plan describing the system boundary, environment, and implemented safeguards."
        ),
    ),
    RequestMergeRule(
        package_title="Configuration Management Plan and Documentation",
        source_titles=(
            "Configuration Management Plan",
            "Configuration Management Documentation",
        ),
        evidence_type=DocumentationRequestType.PLAN,
        description=(
            "Provide the current Configuration Management Plan and related supporting documentation."
        ),
    ),
    RequestMergeRule(
        package_title="Incident Response Plan and Procedures",
        source_titles=(
            "Incident Response Plan",
            "Incident Response Procedures",
        ),
        evidence_type=DocumentationRequestType.PLAN,
        description=(
            "Provide the current Incident Response Plan and supporting procedures."
        ),
    ),
    RequestMergeRule(
        package_title="System Design and Architecture Documentation",
        source_titles=(
            "System Design Documentation",
            "System Architecture Documentation",
            "System Architecture",
        ),
        evidence_type=DocumentationRequestType.DIAGRAM,
        description=(
            "Provide current system design and architecture documentation, including relevant diagrams."
        ),
    ),
    RequestMergeRule(
        package_title="Hardware and System Component Inventory",
        source_titles=(
            "Hardware Inventory",
            "System Component Inventory",
            "Information System Component Inventory",
        ),
        evidence_type=DocumentationRequestType.INVENTORY,
        description=(
            "Provide the current hardware and system component inventory."
        ),
    ),
    RequestMergeRule(
        package_title="Software and Application Inventory",
        source_titles=(
            "Software Inventory",
            "Application Inventory",
            "Installed Software Inventory",
        ),
        evidence_type=DocumentationRequestType.INVENTORY,
        description=(
            "Provide the current software and application inventory."
        ),
    ),
    RequestMergeRule(
        package_title="Media Inventory and Tracking Records",
        source_titles=(
            "Media Inventory",
            "Media Tracking Records",
            "Media Records",
        ),
        evidence_type=DocumentationRequestType.INVENTORY,
        description=(
            "Provide the current media inventory and associated tracking records."
        ),
    ),
    RequestMergeRule(
        package_title="Maintenance Records and Procedures",
        source_titles=(
            "Maintenance Records",
            "System Maintenance Records",
            "Maintenance Procedures",
        ),
        evidence_type=DocumentationRequestType.RECORD,
        description=(
            "Provide maintenance procedures and representative maintenance records."
        ),
    ),
    RequestMergeRule(
        package_title="Security Awareness and Training Records",
        source_titles=(
            "Security Awareness Training Records",
            "Training Records",
            "Security Training Records",
        ),
        evidence_type=DocumentationRequestType.TRAINING_RECORD,
        description=(
            "Provide security awareness and role-based training records for applicable personnel."
        ),
    ),
    RequestMergeRule(
        package_title="Personnel Screening and Authorization Records",
        source_titles=(
            "Personnel Screening Records",
            "Personnel Security Records",
            "Personnel Authorization Records",
        ),
        evidence_type=DocumentationRequestType.PERSONNEL_RECORD,
        description=(
            "Provide personnel screening, security, and authorization records for applicable personnel."
        ),
    ),
    RequestMergeRule(
        package_title="Risk Assessment Documentation",
        source_titles=(
            "Risk Assessment",
            "Risk Assessment Report",
            "Risk Assessment Results",
        ),
        evidence_type=DocumentationRequestType.RISK_ASSESSMENT,
        description=(
            "Provide the current risk assessment and associated results or reports."
        ),
    ),
    RequestMergeRule(
        package_title="Security Assessment Documentation",
        source_titles=(
            "Security Assessment",
            "Security Assessment Report",
            "Security Assessment Results",
        ),
        evidence_type=DocumentationRequestType.SECURITY_ASSESSMENT,
        description=(
            "Provide the current security assessment and associated results or reports."
        ),
    ),
    RequestMergeRule(
        package_title="Plan of Action and Milestones",
        source_titles=(
            "POA&M",
            "POAM",
            "Plan of Action and Milestones",
        ),
        evidence_type=DocumentationRequestType.POAM,
        description=(
            "Provide the current Plan of Action and Milestones for identified weaknesses requiring remediation."
        ),
    ),
)


DEFAULT_SUPPRESS_TITLES: Tuple[str, ...] = (
    "Other Relevant Documents or Records",
)