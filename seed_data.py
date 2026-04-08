"""Seed the database with sample data including FMA analysis"""
from app.database import (
    init_db, create_site, create_process_path, add_process_step,
    create_waste_observation, add_comment, create_failure_mode,
    update_failure_mode, calculate_rpn
)

def seed_data():
    """Add sample data to the database"""
    print("[*] Seeding database with sample data including FMA analysis...")
    
    # Initialize DB
    init_db()
    
    # Create Sites
    print("[+] Creating sites...")
    site1_id = create_site("Portland Fulfillment Center", "PDX1", "Portland, OR", "FC")
    site2_id = create_site("Phoenix Distribution Center", "PHX2", "Phoenix, AZ", "DC")
    site3_id = create_site("Dallas Sortation Center", "DFW3", "Dallas, TX", "SC")
    
    # Create Process Paths
    print("[+] Creating process paths...")
    path1_id = create_process_path(
        site1_id,
        "Inbound Receiving Process",
        "Standard receiving process for inbound shipments",
        "John Smith"
    )
    
    path2_id = create_process_path(
        site1_id,
        "Order Picking Process",
        "Standard order fulfillment and picking workflow",
        "Sarah Johnson"
    )
    
    path3_id = create_process_path(
        site2_id,
        "Cross-Dock Operations",
        "Fast-moving cross-dock process for high velocity items",
        "Mike Chen"
    )
    
    # Add steps to Inbound Receiving
    print("[+] Adding process steps...")
    step1_id = add_process_step(path1_id, "Unload Truck", "Physically unload items from delivery truck")
    step2_id = add_process_step(path1_id, "Quality Check", "Inspect items for damage and verify counts")
    step3_id = add_process_step(path1_id, "Sort by Category", "Organize items by product category")
    step4_id = add_process_step(path1_id, "Label & Tag", "Apply warehouse labels and scan into system")
    step5_id = add_process_step(path1_id, "Put Away", "Transport to storage locations")
    
    # Add steps to Order Picking
    step6_id = add_process_step(path2_id, "Receive Order", "Order appears in pick queue")
    step7_id = add_process_step(path2_id, "Navigate to Location", "Associate travels to pick location")
    step8_id = add_process_step(path2_id, "Pick Item", "Retrieve item from shelf")
    step9_id = add_process_step(path2_id, "Pack Item", "Pack into shipping container")
    
    # Add steps to Cross-Dock
    step10_id = add_process_step(path3_id, "Receive Pallet", "Accept pallet from inbound")
    step11_id = add_process_step(path3_id, "Quick Sort", "Sort items for outbound routes")
    step12_id = add_process_step(path3_id, "Load Outbound", "Load onto outbound truck")
    
    # Add Waste Observations with FMA
    print("[+] Adding waste observations with FMA analysis...")
    
    # Observation 1: Transportation waste (Medium severity)
    obs1_id = create_waste_observation(
        step1_id,
        "Transportation",
        "Truck parking 200ft from dock",
        "Trucks often park far from receiving dock, requiring long manual push of pallets",
        "Medium",
        "John Smith"
    )
    create_failure_mode(obs1_id, occurrence_score=4, detection_score=2, 
                       root_cause="Limited dock parking spaces during peak hours",
                       impact_hours=2.0, impact_cost=250.0)
    
    # Observation 2: Waiting waste (HIGH PRIORITY)
    obs2_id = create_waste_observation(
        step2_id,
        "Waiting",
        "Quality inspector unavailable",
        "Associates wait 15-20 minutes for quality inspector to arrive",
        "High",
        "Sarah Johnson"
    )
    rpn2 = calculate_rpn("High", 8, 3)
    create_failure_mode(obs2_id, occurrence_score=8, detection_score=3,
                       root_cause="Insufficient quality inspector staffing during peak hours",
                       impact_hours=3.5, impact_cost=1500.0)
    update_failure_mode(obs2_id, rpn_score=rpn2, 
                       mitigation_action="Cross-train 2 additional associates as QC inspectors",
                       mitigation_owner="Sarah Johnson",
                       mitigation_due_date="2026-05-15",
                       mitigation_status="In Progress")
    
    # Observation 3: Motion waste
    obs3_id = create_waste_observation(
        step3_id,
        "Motion",
        "Excessive walking to sort bins",
        "Sort bins are spread across 4 different areas requiring constant walking",
        "Medium",
        "Mike Chen"
    )
    rpn3 = calculate_rpn("Medium", 7, 4)
    create_failure_mode(obs3_id, occurrence_score=7, detection_score=4,
                       root_cause="Outdated warehouse layout from 2018 reconfiguration",
                       impact_hours=1.5, impact_cost=800.0)
    update_failure_mode(obs3_id, rpn_score=rpn3,
                       mitigation_action="Consolidate sort bins to 2 central locations",
                       mitigation_owner="Mike Chen",
                       mitigation_due_date="2026-06-01",
                       mitigation_status="Not Started")
    
    # Observation 4: Over-processing waste
    obs4_id = create_waste_observation(
        step4_id,
        "Over-processing",
        "Duplicate label scanning",
        "Associates scan labels twice due to system requirement redundancy",
        "Low",
        "John Smith"
    )
    rpn4 = calculate_rpn("Low", 6, 2)
    create_failure_mode(obs4_id, occurrence_score=6, detection_score=2,
                       root_cause="Legacy ERP system design with redundant validation",
                       impact_hours=0.5, impact_cost=100.0)
    update_failure_mode(obs4_id, rpn_score=rpn4,
                       mitigation_action="Submit IT ticket to remove redundant scan step",
                       mitigation_owner="John Smith",
                       mitigation_due_date="2026-04-30",
                       mitigation_status="Completed")
    
    # Observation 5: Inventory waste (HIGH PRIORITY)
    obs5_id = create_waste_observation(
        step5_id,
        "Inventory",
        "Staged pallets blocking aisles",
        "Pallets wait 2-3 hours in staging before put-away, blocking traffic",
        "High",
        "Sarah Johnson"
    )
    rpn5 = calculate_rpn("High", 9, 2)
    create_failure_mode(obs5_id, occurrence_score=9, detection_score=2,
                       root_cause="Insufficient put-away team capacity during peak receiving",
                       impact_hours=4.0, impact_cost=2000.0)
    update_failure_mode(obs5_id, rpn_score=rpn5,
                       mitigation_action="Hire 2 additional put-away specialists for morning shift",
                       mitigation_owner="Sarah Johnson",
                       mitigation_due_date="2026-05-01",
                       mitigation_status="In Progress")
    
    # Observation 6: Defects (CRITICAL - HIGHEST PRIORITY!)
    obs6_id = create_waste_observation(
        step8_id,
        "Defects",
        "Wrong items picked frequently",
        "10% pick error rate due to confusing bin labels",
        "Critical",
        "Mike Chen"
    )
    rpn6 = calculate_rpn("Critical", 9, 7)
    create_failure_mode(obs6_id, occurrence_score=9, detection_score=7,
                       root_cause="Ambiguous bin labeling system with poor contrast",
                       impact_hours=5.0, impact_cost=5000.0)
    update_failure_mode(obs6_id, rpn_score=rpn6,
                       mitigation_action="Replace all bin labels with high-contrast 3D labels and implement scanner verification",
                       mitigation_owner="Mike Chen",
                       mitigation_due_date="2026-04-20",
                       mitigation_status="In Progress")
    
    # Observation 7: Overproduction
    obs7_id = create_waste_observation(
        step11_id,
        "Overproduction",
        "Sorting items not yet ordered",
        "Pre-sorting items before outbound orders confirmed",
        "Medium",
        "John Smith"
    )
    rpn7 = calculate_rpn("Medium", 5, 5)
    create_failure_mode(obs7_id, occurrence_score=5, detection_score=5,
                       root_cause="Process designed for peak season but running year-round",
                       impact_hours=2.0, impact_cost=600.0)
    update_failure_mode(obs7_id, rpn_score=rpn7,
                       mitigation_action="Implement demand-driven sorting based on confirmed orders",
                       mitigation_owner="John Smith",
                       mitigation_due_date="2026-05-10",
                       mitigation_status="Not Started")
    
    # Observation 8: Inventory waste (additional)
    obs8_id = create_waste_observation(
        step1_id,
        "Inventory",
        "Excess buffer stock piling up",
        "Receiving stock levels 40% above target during slow periods",
        "Medium",
        "Sarah Johnson"
    )
    rpn8 = calculate_rpn("Medium", 6, 3)
    create_failure_mode(obs8_id, occurrence_score=6, detection_score=3,
                       root_cause="Forecasting accuracy issues and safety stock policy",
                       impact_hours=2.5, impact_cost=1200.0)
    update_failure_mode(obs8_id, rpn_score=rpn8,
                       mitigation_action="Review and adjust safety stock parameters in planning system",
                       mitigation_owner="Sarah Johnson",
                       mitigation_due_date="2026-05-20",
                       mitigation_status="On Hold")
    
    # Add Comments
    print("[+] Adding discussion comments...")
    add_comment(obs2_id, "Operations Manager", "Investigating adding a second quality inspector during peak hours")
    add_comment(obs2_id, "Sarah Johnson", "Great idea! We see this issue every morning 8-10am")
    
    add_comment(obs5_id, "Warehouse Lead", "We could dedicate a put-away team instead of ad-hoc assignment")
    add_comment(obs5_id, "Mike Chen", "Let's trial this next week with 2 dedicated associates")
    
    add_comment(obs6_id, "Quality Team", "CRITICAL - This is causing customer complaints. Need immediate action")
    add_comment(obs6_id, "IT Support", "Working on improving bin label visibility with larger font")
    add_comment(obs6_id, "Sarah Johnson", "Also training all pickers on proper verification steps")
    
    add_comment(obs3_id, "Operations Manager", "Layout change approved for budget cycle 2026-Q2")
    add_comment(obs3_id, "Mike Chen", "Great! Will start detailed design work next month")
    
    print("\n[OK] Seed data created successfully!")
    print("\n[=] Summary:")
    print("   - Sites: 3")
    print("   - Process Paths: 3")
    print("   - Process Steps: 12")
    print("   - Waste Observations: 8")
    print("   - FMA Records: 8 (all with RPN scoring)")
    print("   - Comments: 9")
    print("[=] Total Impact Identified:")
    total_cost = 250+1500+800+100+2000+5000+600+1200
    total_hours = 2+3.5+1.5+0.5+4+5+2+2.5
    print("   - Financial: $" + str(total_cost))
    print("   - Hours Lost: " + str(total_hours) + " hours")
    print("\n[!] Run the app with: python run.py")
    print("[!] Visit: http://localhost:8001")

if __name__ == "__main__":
    seed_data()
