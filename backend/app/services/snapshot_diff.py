"""
Snapshot Diff Engine
Deterministic comparison of compliance state between two snapshots.
"""

import hashlib
import json
from datetime import datetime
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum


class DiffSeverity(str, Enum):
    CRITICAL = "critical"  # Requires immediate policy update
    HIGH = "high"  # Requires review, likely policy update
    MEDIUM = "medium"  # Should review, may need policy update
    LOW = "low"  # Informational, document only


@dataclass
class FieldChange:
    """Single field-level change."""
    field_path: str
    old_value: any
    new_value: any
    change_type: str  # 'added', 'removed', 'modified'
    severity: DiffSeverity
    reason: str


@dataclass
class EntityDiff:
    """Changes for a specific entity."""
    entity_type: str
    entity_id: str
    entity_name: str
    change_type: str  # 'added', 'removed', 'modified'
    field_changes: List[FieldChange]
    overall_severity: DiffSeverity


class SnapshotDiffEngine:
    """
    Deterministic diff engine for compliance snapshots.
    NO LLM INVOLVED - pure structured comparison.
    """
    
    # Fields that always trigger material change
    MATERIAL_FIELDS = {
        'questionnaire': [
            'collects_consumer_health_data',
            'targets_washington_residents',
            'revenue_over_25m',
            'processes_precise_geolocation',
            'uses_advertising_cookies',
        ],
        'vendor': [
            'processes_health_data',
            'is_ad_tech',
            'data_categories',
            'location',
        ],
        'data_element': [
            'mhmda_category',
            'health_signal',
            'storage_location',
        ]
    }
    
    def __init__(self):
        self.material_changes = []
        self.all_changes = []
    
    def compare_snapshots(
        self,
        baseline: Dict,
        current: Dict
    ) -> Dict:
        """
        Compare two compliance snapshots and return diff report.
        
        Returns structured diff with severity classification.
        """
        diffs = []
        
        # Compare questionnaire responses
        questionnaire_diffs = self._compare_questionnaire(
            baseline.get('questionnaire_responses', {}),
            current.get('questionnaire_responses', {})
        )
        diffs.extend(questionnaire_diffs)
        
        # Compare vendors
        vendor_diffs = self._compare_vendors(
            baseline.get('vendors', {}),
            current.get('vendors', {})
        )
        diffs.extend(vendor_diffs)
        
        # Compare data elements
        element_diffs = self._compare_data_elements(
            baseline.get('data_elements', {}),
            current.get('data_elements', {})
        )
        diffs.extend(element_diffs)
        
        # Compare policy inputs
        policy_diffs = self._compare_policy_inputs(
            baseline.get('policy_inputs', {}),
            current.get('policy_inputs', {})
        )
        diffs.extend(policy_diffs)
        
        return self._compile_report(diffs)
    
    def _compare_questionnaire(
        self,
        baseline: Dict,
        current: Dict
    ) -> List[EntityDiff]:
        """Compare questionnaire responses."""
        diffs = []
        
        # Get all keys
        all_keys = set(baseline.keys()) | set(current.keys())
        
        for key in all_keys:
            old_val = baseline.get(key)
            new_val = current.get(key)
            
            if old_val != new_val:
                is_material = key in self.MATERIAL_FIELDS['questionnaire']
                
                field_change = FieldChange(
                    field_path=f"questionnaire.{key}",
                    old_value=old_val,
                    new_value=new_val,
                    change_type=self._classify_change(old_val, new_val),
                    severity=DiffSeverity.CRITICAL if is_material else DiffSeverity.MEDIUM,
                    reason=f"Applicability input changed: may affect MHMDA scope"
                )
                
                diff = EntityDiff(
                    entity_type='questionnaire',
                    entity_id='primary',
                    entity_name='Applicability Assessment',
                    change_type=self._classify_change(old_val, new_val),
                    field_changes=[field_change],
                    overall_severity=field_change.severity
                )
                
                diffs.append(diff)
        
        return diffs
    
    def _compare_vendors(
        self,
        baseline: Dict[str, Dict],
        current: Dict[str, Dict]
    ) -> List[EntityDiff]:
        """Compare vendor configurations."""
        diffs = []
        baseline_ids = set(baseline.keys())
        current_ids = set(current.keys())
        
        # Added vendors
        for vendor_id in current_ids - baseline_ids:
            vendor = current[vendor_id]
            diffs.append(self._create_vendor_diff(
                vendor_id, vendor, 'added'
            ))
        
        # Removed vendors
        for vendor_id in baseline_ids - current_ids:
            vendor = baseline[vendor_id]
            diffs.append(self._create_vendor_diff(
                vendor_id, vendor, 'removed'
            ))
        
        # Modified vendors
        for vendor_id in baseline_ids & current_ids:
            old_vendor = baseline[vendor_id]
            new_vendor = current[vendor_id]
            
            field_changes = []
            for field in self.MATERIAL_FIELDS['vendor']:
                old_val = old_vendor.get(field)
                new_val = new_vendor.get(field)
                
                if old_val != new_val:
                    field_changes.append(FieldChange(
                        field_path=f"vendor.{field}",
                        old_value=old_val,
                        new_value=new_val,
                        change_type='modified',
                        severity=DiffSeverity.HIGH,
                        reason=f"Vendor {field} changed - may affect data processing disclosures"
                    ))
            
            if field_changes:
                diffs.append(EntityDiff(
                    entity_type='vendor',
                    entity_id=vendor_id,
                    entity_name=new_vendor.get('name', 'Unknown'),
                    change_type='modified',
                    field_changes=field_changes,
                    overall_severity=DiffSeverity.HIGH
                ))
        
        return diffs
    
    def _compare_data_elements(
        self,
        baseline: Dict[str, Dict],
        current: Dict[str, Dict]
    ) -> List[EntityDiff]:
        """Compare data element inventory."""
        diffs = []
        baseline_ids = set(baseline.keys())
        current_ids = set(current.keys())
        
        # Count by category for summary
        old_categories = self._categorize_elements(baseline)
        new_categories = self._categorize_elements(current)
        
        # Check for category shifts (material)
        for category in set(old_categories.keys()) | set(new_categories.keys()):
            old_count = old_categories.get(category, 0)
            new_count = new_categories.get(category, 0)
            
            if old_count != new_count and category.startswith('health_'):
                diffs.append(EntityDiff(
                    entity_type='data_category',
                    entity_id=category,
                    entity_name=f'{category} elements',
                    change_type='modified',
                    field_changes=[FieldChange(
                        field_path=f'data_elements.{category}.count',
                        old_value=old_count,
                        new_value=new_count,
                        change_type='modified',
                        severity=DiffSeverity.HIGH,
                        reason=f"Health-related data category count changed from {old_count} to {new_count}"
                    )],
                    overall_severity=DiffSeverity.HIGH
                ))
        
        # Check specific element changes
        for element_id in baseline_ids & current_ids:
            old_elem = baseline[element_id]
            new_elem = current[element_id]
            
            for field in self.MATERIAL_FIELDS['data_element']:
                old_val = old_elem.get(field)
                new_val = new_elem.get(field)
                
                if old_val != new_val:
                    diffs.append(EntityDiff(
                        entity_type='data_element',
                        entity_id=element_id,
                        entity_name=new_elem.get('name', 'Unknown'),
                        change_type='modified',
                        field_changes=[FieldChange(
                            field_path=f'data_element.{field}',
                            old_value=old_val,
                            new_value=new_val,
                            change_type='modified',
                            severity=DiffSeverity.CRITICAL,
                            reason=f"Element classification changed - affects data inventory accuracy"
                        )],
                        overall_severity=DiffSeverity.CRITICAL
                    ))
        
        return diffs
    
    def _compare_policy_inputs(
        self,
        baseline: Dict,
        current: Dict
    ) -> List[EntityDiff]:
        """Compare policy generation inputs."""
        diffs = []
        
        # Compare hash of policy inputs
        baseline_hash = self._hash_inputs(baseline)
        current_hash = self._hash_inputs(current)
        
        if baseline_hash != current_hash:
            diffs.append(EntityDiff(
                entity_type='policy',
                entity_id='inputs',
                entity_name='Policy Generation Inputs',
                change_type='modified',
                field_changes=[FieldChange(
                    field_path='policy_inputs_hash',
                    old_value=baseline_hash,
                    new_value=current_hash,
                    change_type='modified',
                    severity=DiffSeverity.HIGH,
                    reason="Policy inputs changed - policy regeneration may be required"
                )],
                overall_severity=DiffSeverity.HIGH
            ))
        
        return diffs
    
    def _create_vendor_diff(
        self,
        vendor_id: str,
        vendor: Dict,
        change_type: str
    ) -> EntityDiff:
        """Create diff entry for added/removed vendor."""
        severity = DiffSeverity.CRITICAL if vendor.get('processes_health_data') else DiffSeverity.MEDIUM
        
        return EntityDiff(
            entity_type='vendor',
            entity_id=vendor_id,
            entity_name=vendor.get('name', 'Unknown'),
            change_type=change_type,
            field_changes=[],
            overall_severity=severity
        )
    
    def _categorize_elements(self, elements: Dict) -> Dict[str, int]:
        """Count elements by category."""
        categories = {}
        for elem in elements.values():
            cat = elem.get('mhmda_category', 'other')
            categories[cat] = categories.get(cat, 0) + 1
        return categories
    
    def _classify_change(self, old_val, new_val) -> str:
        """Classify type of change."""
        if old_val is None and new_val is not None:
            return 'added'
        if old_val is not None and new_val is None:
            return 'removed'
        return 'modified'
    
    def _hash_inputs(self, inputs: Dict) -> str:
        """Create deterministic hash of inputs."""
        normalized = json.dumps(inputs, sort_keys=True, default=str)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _compile_report(self, diffs: List[EntityDiff]) -> Dict:
        """Compile diffs into final report."""
        material_count = sum(1 for d in diffs if d.overall_severity in [DiffSeverity.CRITICAL, DiffSeverity.HIGH])
        
        return {
            'total_changes': len(diffs),
            'material_changes': material_count,
            'critical': sum(1 for d in diffs if d.overall_severity == DiffSeverity.CRITICAL),
            'high': sum(1 for d in diffs if d.overall_severity == DiffSeverity.HIGH),
            'medium': sum(1 for d in diffs if d.overall_severity == DiffSeverity.MEDIUM),
            'low': sum(1 for d in diffs if d.overall_severity == DiffSeverity.LOW),
            'requires_policy_regeneration': any(
                d.overall_severity == DiffSeverity.CRITICAL for d in diffs
            ),
            'changes': [
                {
                    'entity_type': d.entity_type,
                    'entity_id': d.entity_id,
                    'entity_name': d.entity_name,
                    'change_type': d.change_type,
                    'severity': d.overall_severity.value,
                    'fields': [
                        {
                            'path': f.field_path,
                            'old': f.old_value,
                            'new': f.new_value,
                            'reason': f.reason
                        }
                        for f in d.field_changes
                    ]
                }
                for d in sorted(diffs, key=lambda x: (
                    x.overall_severity == DiffSeverity.CRITICAL,
                    x.overall_severity == DiffSeverity.HIGH
                ), reverse=True)
            ],
            'generated_at': datetime.utcnow().isoformat()
        }
