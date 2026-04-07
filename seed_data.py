"""Seed the database with sample data"""
from app.database import (
    init_db, create_site, create_process_path, add_process_step,
    create_waste_observation, add_comment
)

def seed_data():
    """Add sample data to the database"""
    print("Seeding database with sample data...")
    
    # Initialize DB
    init_db()
    
    # Create Sites
    print("Creating sites...")
    site1_id = create_site("Portland Fulfillment Center", "PDX1", "Portland, OR", "FC")
    site2_id = create_site("Phoenix Distribution Center", "PHX2", "Phoenix, AZ", "DC")
    site3_id = create_site("Dallas Sortation Center", "DFW3", "Dallas, TX", "SC")
    
    # Create Process Paths
    print("Creating process paths...")
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
    print("Adding process steps...")
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
    
    # Add Waste Observations
    print("Adding waste observations...")
    
    # Transportation waste
    obs1_id = create_waste_observation(
        step1_id,
        "Transportation",
        "Truck parking 200ft from dock",
        "Trucks often park far from receiving dock, requiring long manual push of pallets",
        "Medium",
        "John Smith"
    )
    
    # Waiting waste
    obs2_id = create_waste_observation(
        step2_id,
        "Waiting",
        "Quality inspector unavailable",
        "Associates wait 15-20 minutes for quality inspector to arrive",
        "High",
        "Sarah Johnson"
    )
    
    # Motion waste
    obs3_id = create_waste_observation(
        step3_id,
        "Motion",
        "Excessive walking to sort bins",
        "Sort bins are spread across 4 different areas requiring constant walking",
        "Medium",
        "Mike Chen"
    )
    
    # Over-processing waste
    obs4_id = create_waste_observation(
        step4_id,
        "Over-processing",
        "Duplicate label scanning",
        "Associates scan labels twice due to system requirement redundancy",
        "Low",
        "John Smith"
    )
    
    # Inventory waste
    obs5_id = create_waste_observation(
        step5_id,
        "Inventory",
        "Staged pallets blocking aisles",
        "Pallets wait 2-3 hours in staging before put-away, blocking traffic",
        "High",
        "Sarah Johnson"
    )
    
    # Defects
    obs6_id = create_waste_observation(
        step8_id,
        "Defects",
        "Wrong items picked frequently",
        "10% pick error rate due to confusing bin labels",
        "Critical",
        "Mike Chen"
    )
    
    # Overproduction
    obs7_id = create_waste_observation(
        step11_id,
        "Overproduction",
        "Sorting items not yet ordered",
        "Pre-sorting items before outbound orders confirmed",
        "Medium",
        "John Smith"
    )
    
    # Add Comments
    print("Adding comments...")
    add_comment(obs2_id, "Operations Manager", "Investigating adding a second quality inspector during peak hours")
    add_comment(obs2_id, "Sarah Johnson", "Great idea! We see this issue every morning 8-10am")
    
    add_comment(obs5_id, "Warehouse Lead", "We could dedicate a put-away team instead of ad-hoc assignment")
    add_comment(obs5_id, "Mike Chen", "Let's trial this next week with 2 dedicated associates")
    
    add_comment(obs6_id, "Quality Team", "CRITICAL - This is causing customer complaints. Need immediate action")
    add_comment(obs6_id, "IT Support", "Working on improving bin label visibility with larger font")
    add_comment(obs6_id, "Sarah Johnson", "Also training all pickers on proper verification steps")
    
    print("Seed data created successfully!")
    print("\nSummary:")
    print(f"  - Sites: 3")
    print(f"  - Process Paths: 3")
    print(f"  - Process Steps: 12")
    print(f"  - Waste Observations: 7")
    print(f"  - Comments: 7")
    print("\nRun the app with: python run.py")

if __name__ == "__main__":
    seed_data()
