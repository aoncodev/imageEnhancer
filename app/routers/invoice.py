from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse


router = APIRouter()


@router.post("/generate-invoice")
async def generate_invoice(data: dict):
    """
    Request example:
    {
        "amount": 100,
        "currency": "USD",
        "recipient": "John Doe"
    }

    Response:
    {
        "invoice_id": "12345",
        "status": "generated"
    }
    """
    try:
        # Simulate invoice generation logic
        invoice_id = "12345"
        return JSONResponse(content={"invoice_id": invoice_id, "status": "generated", "data": data})

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
