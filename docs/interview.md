# Interview explanations

- **Containers vs managed services:** Nginx and Gunicorn are processes packaged into containers on EC2. RDS and S3 are AWS-managed data services; Compose does not manage their availability or backups.
- **Compose vs Swarm secrets:** Compose binds protected host files into containers. Swarm has encrypted secret distribution/storage. Compose files are not automatically encrypted at rest.
- **IAM roles vs keys:** The instance role supplies rotating temporary credentials through the SDK default chain. Hard-coded access keys create long-lived leak and rotation risks.
- **EC2-to-RDS security groups:** RDS accepts 3306 only from ENIs bearing the app security group. Authentication, database privileges and verified TLS are still required.
- **Private S3:** Block Public Access and scoped role permissions keep objects inaccessible anonymously. The app checks ownership before reading an object.
- **Presigned authorization:** Signing an object URL alone is not user authorization. Check ownership first; a short-lived signed URL is a transferable bearer credential. This implementation instead returns bytes through the authorized app.
- **Migrations:** Versioned schema changes track database evolution. Run once per release with a privileged migration identity; routine HTTP requests use a DML-only account.
- **Availability:** One EC2 host and Single-AZ RDS have failure/maintenance downtime. Compose restart policies do not provide multi-host scheduling or load balancing.
- **Persistence:** Container recreation discards writable layers. Cloud records live in RDS and bytes in S3. Local MySQL has a named volume; the Moto emulator is ephemeral. Secret files reside on the EC2 disk and need retrieval after host replacement.
- **Partial failures:** S3 and MySQL cannot share one transaction. Upload compensation reduces orphans but cannot eliminate crash windows; deletion can leave metadata pending a retry.
