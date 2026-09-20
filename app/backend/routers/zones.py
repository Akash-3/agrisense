from fastapi import APIRouter, HTTPException, Depends
import time
from dependencies import get_current_user
from models.schemas import ZoneCreate, ZoneUpdate, CropCreate, CropUpdate
from database import (
    get_farm_owner, get_zone_owner, get_crop_owner, create_zone, get_zones_by_farm, 
    update_zone, create_crop, get_crops_by_zone, get_active_crop_by_zone, update_crop, execute_db
)

router = APIRouter(tags=["Zones & Crops"])

@router.get("/api/v1/farms/{farm_id}/zones")
def list_zones(farm_id: int, current_user: int = Depends(get_current_user)):
    owner = get_farm_owner(farm_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    if owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this farm")
    return {"status": "success", "zones": get_zones_by_farm(farm_id)}

@router.post("/api/v1/farms/{farm_id}/zones")
def add_zone(farm_id: int, req: ZoneCreate, current_user: int = Depends(get_current_user)):
    owner = get_farm_owner(farm_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    if owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this farm")
    res = create_zone(farm_id, req.zone_name, req.acres, req.polygon_coords)
    return {"status": "success", "zone_id": res}

@router.put("/api/v1/zones/{zone_id}")
def edit_zone(zone_id: int, req: ZoneUpdate, current_user: int = Depends(get_current_user)):
    owner = get_zone_owner(zone_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    if owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this zone")
    update_zone(zone_id, req.zone_name, req.acres, req.polygon_coords)
    return {"status": "success"}

@router.get("/api/v1/zones/{zone_id}/crops")
def list_crops(zone_id: int, current_user: int = Depends(get_current_user)):
    owner = get_zone_owner(zone_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    if owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this zone")
    return {"status": "success", "crops": get_crops_by_zone(zone_id)}

@router.post("/api/v1/zones/{zone_id}/crops")
def add_crop(zone_id: int, req: CropCreate, current_user: int = Depends(get_current_user)):
    owner = get_zone_owner(zone_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    if owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this zone")
    
    if req.status == "PLANTED":
        active_crop_id = get_active_crop_by_zone(zone_id)
        if active_crop_id:
            raise HTTPException(status_code=409, detail="Zone already has an active PLANTED crop")
            
    res = create_crop(zone_id, req.crop_name, req.status, req.planted_date or time.time())
    return {"status": "success", "crop_id": res}

@router.put("/api/v1/crops/{crop_id}")
def edit_crop(crop_id: int, req: CropUpdate, current_user: int = Depends(get_current_user)):
    owner = get_crop_owner(crop_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Crop not found")
    if owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this crop")
        
    if req.status == "PLANTED":
        res = execute_db("SELECT zone_id FROM crops WHERE id = ?", (crop_id,), fetchone=True)
        if res:
            zone_id = res[0]
            active_crop_id = get_active_crop_by_zone(zone_id)
            if active_crop_id and active_crop_id != crop_id:
                raise HTTPException(status_code=409, detail="Zone already has an active PLANTED crop")

    update_crop(crop_id, req.crop_name, req.status)
    return {"status": "success"}

from models.schemas import DeviceAssignRequest
from database import assign_device, get_devices_for_farm

@router.get("/api/v1/farms/{farm_id}/devices")
def get_farm_devices_endpoint(farm_id: int, current_user: int = Depends(get_current_user)):
    owner = get_farm_owner(farm_id)
    if owner is None:
        raise HTTPException(status_code=404, detail="Farm not found")
    if owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this farm")
    
    devices = get_devices_for_farm(farm_id)
    return {"status": "success", "devices": devices}

@router.post("/api/v1/devices/assign")
def assign_device_endpoint(req: DeviceAssignRequest, current_user: int = Depends(get_current_user)):
    # 1. Verify the DESTINATION zone belongs to the authenticated farmer.
    dest_owner = get_zone_owner(req.zone_id)
    if dest_owner is None:
        raise HTTPException(status_code=404, detail="Zone not found")
    if dest_owner != current_user:
        raise HTTPException(status_code=403, detail="Not authorized to access this zone")

    # 2. If device already exists, verify the authenticated farmer owns it.
    from database import get_device_by_device_id
    existing = get_device_by_device_id(req.device_id)
    if existing:
        current_zone_owner = get_zone_owner(existing["zone_id"])
        if current_zone_owner != current_user:
            raise HTTPException(
                status_code=403,
                detail="Device belongs to another farmer and cannot be reassigned"
            )

    assign_device(req.device_id, req.zone_id, req.device_type, expected_owner_id=current_user)
    return {"status": "success", "device_id": req.device_id, "zone_id": req.zone_id}


