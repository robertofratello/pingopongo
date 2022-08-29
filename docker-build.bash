docker run --privileged --rm tonistiigi/binfmt --install all && docker buildx build --platform linux/arm/v7,linux/arm64/v8,linux/amd64 --tag guglielmofelici/pingopongo-be --push . || { echo "May need to run as sudo." && exit 1; }