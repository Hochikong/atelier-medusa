## 启动基于celery的异步服务：

windows下启动必须指定pool为solo或者threads，linux下则无所谓。如果需要定时调度worker，则需要配置启动celery beat

```powershell
PS C:\Users\ckhoi\PycharmProjects\atelier-medusa\MCF-2-Flash> celery -A MCF2Flash.celery_core worker --loglevel=info --pool=solo 
PS C:\Users\ckhoi\PycharmProjects\atelier-medusa\MCF-2-Flash> celery -A MCF2Flash.celery_core beat --loglevel=info 
```



## 启动FastAPI：

```powershell
PS C:\Users\ckhoi\PycharmProjects\atelier-medusa\MCF-2-Flash> uvicorn MCF2Flash.rest_core:app --host 0.0.0.0 --port 8081
```