import asyncio
import logging

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages docker-compose lifecycle for the RAG application."""

    def __init__(
        self, docker_compose_path: str, project_name: str, mode: str
    ) -> None:
        """
        Initialize DockerManager.

        Args:
            docker_compose_path: Path to the directory containing docker-compose.yml
            project_name: Project name for docker-compose operations
            mode: LLM mode ("docker" or "ollama")
        """
        self.docker_compose_path = docker_compose_path
        self.project_name = project_name
        self.mode = mode

    async def start(self) -> bool:
        """
        Start docker-compose services.

        Returns:
            True if successful, False otherwise
        """
        if self.mode != "docker":
            logger.info("Docker mode disabled, skipping docker-compose start")
            return True

        try:
            logger.info(f"Starting docker-compose services from {self.docker_compose_path}...")
            result = await self._run_command(
                [
                    "docker-compose",
                    "-f",
                    f"{self.docker_compose_path}/docker-compose.yml",
                    "-p",
                    self.project_name,
                    "up",
                    "-d",
                ]
            )
            if result:
                logger.info("docker-compose services started successfully")
                return True
            else:
                logger.error("Failed to start docker-compose services")
                return False
        except Exception as e:
            logger.error(f"Error starting docker-compose: {e}")
            return False

    async def stop(self) -> bool:
        """
        Stop docker-compose services.

        Returns:
            True if successful, False otherwise
        """
        if self.mode != "docker":
            logger.info("Docker mode disabled, skipping docker-compose stop")
            return True

        try:
            logger.info("Stopping docker-compose services...")
            result = await self._run_command(
                [
                    "docker-compose",
                    "-f",
                    f"{self.docker_compose_path}/docker-compose.yml",
                    "-p",
                    self.project_name,
                    "down",
                ]
            )
            if result:
                logger.info("docker-compose services stopped successfully")
                return True
            else:
                logger.error("Failed to stop docker-compose services")
                return False
        except Exception as e:
            logger.error(f"Error stopping docker-compose: {e}")
            return False

    async def is_running(self) -> bool:
        """
        Check if docker-compose services are running.

        Returns:
            True if services are running, False otherwise
        """
        if self.mode != "docker":
            return True

        try:
            result = await self._run_command(
                [
                    "docker-compose",
                    "-f",
                    f"{self.docker_compose_path}/docker-compose.yml",
                    "-p",
                    self.project_name,
                    "ps",
                    "-q",
                ]
            )
            return result
        except Exception as e:
            logger.error(f"Error checking docker-compose status: {e}")
            return False

    async def _run_command(self, command: list[str]) -> bool:
        """
        Run a command asynchronously.

        Args:
            command: Command and arguments to run

        Returns:
            True if command succeeded (return code 0), False otherwise

        Raises:
            Exception: If command execution fails
        """
        try:
            process = await asyncio.create_subprocess_exec(
                *command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode != 0:
                error_msg = stderr.decode() if stderr else "Unknown error"
                logger.error(f"Command failed: {' '.join(command)}\nError: {error_msg}")
                return False

            return True
        except FileNotFoundError:
            raise Exception(
                "docker-compose not found. Please ensure docker and docker-compose are installed."
            )
        except Exception as e:
            raise Exception(f"Failed to execute command {' '.join(command)}: {e}")
