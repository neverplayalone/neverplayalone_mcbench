# Runtime image for sandboxed benchmark agents.
#
# The allowed agent dependencies (mineflayer & friends) are installed ONCE into
# /opt/agent-runtime. At run time the agent's own directory is bind-mounted
# read-only at /agent; NODE_PATH points back at the baked node_modules so the
# volume never shadows the dependencies. Agent code is therefore never built or
# `npm install`ed per run — it just runs against this image.
FROM node:22-bookworm-slim

# Install the shared dependency set into a path outside the agent mount point.
WORKDIR /opt/agent-runtime
COPY package.json package-lock.json ./
RUN npm ci --omit=dev && npm cache clean --force

# Resolve requires from the baked deps; keep any stray writes off the read-only
# rootfs by pointing HOME at the tmpfs mounted at run time.
ENV NODE_PATH=/opt/agent-runtime/node_modules \
    NODE_ENV=production \
    HOME=/tmp

# Drop to the unprivileged user the node image ships with.
USER node
WORKDIR /agent
CMD ["node", "index.js"]
