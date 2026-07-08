from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.site import Site


router = APIRouter()


@router.get("")
def list_sites(db: Session = Depends(get_db)) -> list[dict]:
    sites = db.query(Site).order_by(Site.id.asc()).all()
    return [
        {
            "id": site.id,
            "site_code": site.site_code,
            "site_name": site.site_name,
            "contact_name": site.contact_name,
            "contact_phone": site.contact_phone,
        }
        for site in sites
    ]
