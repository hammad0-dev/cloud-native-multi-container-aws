# Evidence checklist

Never invent screenshots, logs or outcomes. Sanitize account IDs, public addresses as appropriate and remove secrets, cookies and document contents before publication.

- [x] Local pytest result recorded in [validation.md](validation.md): 20 passed.
- [x] Local image built and four services healthy; results recorded in validation.md.
- [x] Automated real HTTP smoke passed through Nginx with dummy data; browser screenshots remain optional evidence to capture.
- [x] Terraform fmt/init/validate results recorded in [validation.md](validation.md); security scanner unavailable.
- [ ] Capture reviewed plan; keep raw plan/state private.
- [ ] EC2 deployment/version/instance profile/IMDSv2 — **capture after deployment**.
- [ ] RDS private accessibility, SG source, TLS verification — **capture after deployment**.
- [ ] S3 Block Public Access, encryption, TLS policy and scoped role — **capture after deployment**.
- [ ] Runtime S3 put/get/delete and app owner isolation — **capture after deployment**.
- [ ] RDS snapshot/data preservation decision and reviewed destroy plan — **capture after deployment**.
- [ ] Actual cleanup and residual billing review — **capture after deployment**.

Record date, region, source commit/image digest, command exit status and limitations with each piece of evidence. Keep this checklist incomplete until evidence exists.
