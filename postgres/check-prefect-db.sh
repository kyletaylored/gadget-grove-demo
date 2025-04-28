echo 'Waiting for PostgreSQL to be ready...'
until PGPASSWORD=${POSTGRES_PASSWORD} pg_isready -h postgres-db -U ${POSTGRES_USER}; do
    echo 'PostgreSQL not ready, retrying...'
    sleep 1
done

echo 'PostgreSQL is ready, waiting for Prefect database...'
until PGPASSWORD=${POSTGRES_PASSWORD} psql -h postgres-db -U ${POSTGRES_USER} -d postgres -c "SELECT 1 FROM pg_database WHERE datname='${PREFECT_DB}'" | grep -q 1; do
    echo 'Waiting for Prefect database to be created...'
    sleep 2
done
echo 'Prefect database is now available!'