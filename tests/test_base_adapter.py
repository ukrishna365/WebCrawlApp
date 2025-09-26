"""
Test script for adapters/base.py to validate the base adapter infrastructure.

Run this with: python tests/test_base_adapter.py
"""

import asyncio
from unittest.mock import Mock, patch
from adapters.base import BaseAdapter, AdapterRegistry, register_adapter, get_best_adapter
from app.schemas import (
    ContentBlock, ContentType, Capability, AdapterType,
    DetectionResult, ExtractionResult, AdapterConfig
)


class MockAdapter(BaseAdapter):
    """Mock adapter for testing the base adapter functionality."""
    
    @property
    def adapter_type(self) -> AdapterType:
        return AdapterType.HTML
    
    @property
    def supported_capabilities(self) -> set[Capability]:
        return {Capability.SECTION, Capability.NAV_GRAPH}
    
    async def can_handle(self, url: str, content_type: str = None, 
                        content_preview: str = None) -> DetectionResult:
        """Mock detection logic."""
        if "test.com" in url:
            return DetectionResult(
                adapter_type=self.adapter_type,
                confidence=0.9,
                content_type="text/html",
                host="test.com",
                title="Test Page",
                description="A test page",
                metadata={"test": True}
            )
        else:
            return DetectionResult(
                adapter_type=self.adapter_type,
                confidence=0.1,
                content_type="text/html",
                host="unknown.com",
                title="Unknown Page"
            )
    
    async def extract_content(self, url: str, capabilities: list[Capability],
                            max_depth: int = 1) -> ExtractionResult:
        """Mock content extraction."""
        blocks = []
        
        if Capability.SECTION in capabilities:
            block = self.create_content_block(
                content_type=ContentType.SECTION,
                content="This is a test section with some content. " * 3,
                url=url,
                title="Test Section",
                metadata={"capability": "section"}
            )
            blocks.append(block)
        
        if Capability.NAV_GRAPH in capabilities:
            block = self.create_content_block(
                content_type=ContentType.NAV_BAR,
                content="Home | About | Contact | Services | Products | Documentation | Support | Contact Us | Help Center | FAQ",
                url=url,
                title="Navigation",
                metadata={"capability": "nav_graph"}
            )
            blocks.append(block)
        
        return ExtractionResult(
            content_blocks=blocks,
            extraction_stats={"total_blocks": len(blocks)},
            adapter_used=self.adapter_type,
            capabilities_provided=capabilities
        )


class MockCodeAdapter(BaseAdapter):
    """Mock code repository adapter for testing."""
    
    @property
    def adapter_type(self) -> AdapterType:
        return AdapterType.CODE_REPO
    
    @property
    def supported_capabilities(self) -> set[Capability]:
        return {Capability.CODE_MAP, Capability.README, Capability.MANIFEST}
    
    async def can_handle(self, url: str, content_type: str = None, 
                        content_preview: str = None) -> DetectionResult:
        """Mock detection for GitHub URLs."""
        if "github.com" in url:
            return DetectionResult(
                adapter_type=self.adapter_type,
                confidence=0.95,
                content_type="text/html",
                host="github.com",
                title="GitHub Repository",
                description="A GitHub repository",
                metadata={"repository": True}
            )
        else:
            return DetectionResult(
                adapter_type=self.adapter_type,
                confidence=0.1,
                content_type="text/html",
                host="unknown.com"
            )
    
    async def extract_content(self, url: str, capabilities: list[Capability],
                            max_depth: int = 1) -> ExtractionResult:
        """Mock code repository extraction."""
        blocks = []
        
        if Capability.CODE_MAP in capabilities:
            block = self.create_content_block(
                content_type=ContentType.CODE_MAP,
                content="def hello_world():\n    print('Hello, World!')\n\nclass MyClass:\n    def __init__(self):\n        self.value = 'test'\n\nimport os\nimport sys\n\n# This is a longer code example with multiple functions and classes",
                url=url,
                title="Main Code File",
                metadata={"file_type": "python"}
            )
            blocks.append(block)
        
        return ExtractionResult(
            content_blocks=blocks,
            extraction_stats={"total_blocks": len(blocks)},
            adapter_used=self.adapter_type,
            capabilities_provided=capabilities
        )


def test_base_adapter_initialization():
    """Test base adapter initialization."""
    print("Testing Base Adapter Initialization...")
    
    adapter = MockAdapter()
    
    assert adapter.adapter_type == AdapterType.HTML
    assert Capability.SECTION in adapter.supported_capabilities
    assert Capability.NAV_GRAPH in adapter.supported_capabilities
    assert len(adapter.supported_capabilities) == 2
    
    print("Base adapter initialization working correctly")


def test_content_quality_scoring():
    """Test content quality scoring."""
    print("Testing Content Quality Scoring...")
    
    adapter = MockAdapter()
    
    # Test high quality content
    high_quality_score = adapter.score_content_quality(
        "# Header\n\nThis is a well-structured document with headers and content. " * 2,
        ContentType.SECTION
    )
    assert high_quality_score > 0.8
    
    # Test low quality content
    low_quality_score = adapter.score_content_quality(
        "Short",
        ContentType.SECTION
    )
    assert low_quality_score < 0.5
    
    # Test code content
    code_score = adapter.score_content_quality(
        "def function_name():\n    return 'hello world'\n\nclass MyClass:\n    def __init__(self):\n        self.value = 'test'\n\nimport os\nimport sys",
        ContentType.CODE_MAP
    )
    
    assert code_score > 0.7
    
    print("Content quality scoring working correctly")


def test_content_block_creation():
    """Test content block creation with validation."""
    print("Testing Content Block Creation...")
    
    adapter = MockAdapter()
    
    # Test valid content block
    block = adapter.create_content_block(
        content_type=ContentType.SECTION,
        content="This is a valid content block with sufficient length and quality. " * 2,
        url="https://example.com/page",
        title="Test Page",
        metadata={"test": True}
    )
    
    assert block.content_type == ContentType.SECTION
    assert block.title == "Test Page"
    assert str(block.url) == "https://example.com/page"
    assert block.metadata["test"] == True
    assert block.score > 0.0
    assert block.char_count == len(block.content)
    
    # Test invalid content (too short)
    try:
        adapter.create_content_block(
            content_type=ContentType.SECTION,
            content="Short",
            url="https://example.com/page"
        )
        assert False, "Should have raised ValueError for short content"
    except ValueError as e:
        assert "Content too short" in str(e)
    
    print("Content block creation working correctly")


def test_capability_mapping():
    """Test capability mapping from questions."""
    print("Testing Capability Mapping...")
    
    adapter = MockAdapter()
    
    # Test navigation question
    nav_capabilities = adapter.get_capabilities_for_question("How do I navigate to the settings page?")
    assert Capability.NAV_GRAPH in nav_capabilities
    
    # Test documentation question
    doc_capabilities = adapter.get_capabilities_for_question("Where can I find the documentation?")
    assert Capability.SECTION in doc_capabilities
    
    # Test mixed question
    mixed_capabilities = adapter.get_capabilities_for_question("How do I navigate the code structure?")
    assert len(mixed_capabilities) >= 1
    
    print("Capability mapping working correctly")


def test_adapter_registry():
    """Test adapter registry functionality."""
    print("Testing Adapter Registry...")
    
    registry = AdapterRegistry()
    
    # Test empty registry
    assert len(registry.list_adapters()) == 0
    
    # Test adapter registration
    adapter1 = MockAdapter()
    adapter2 = MockCodeAdapter()
    
    registry.register_adapter(adapter1)
    registry.register_adapter(adapter2)
    
    assert len(registry.list_adapters()) == 2
    assert AdapterType.HTML in registry.list_adapters()
    assert AdapterType.CODE_REPO in registry.list_adapters()
    
    # Test getting adapter by type
    html_adapter = registry.get_adapter_by_type(AdapterType.HTML)
    assert html_adapter is not None
    assert html_adapter.adapter_type == AdapterType.HTML
    
    code_adapter = registry.get_adapter_by_type(AdapterType.CODE_REPO)
    assert code_adapter is not None
    assert code_adapter.adapter_type == AdapterType.CODE_REPO
    
    print("Adapter registry working correctly")


async def test_adapter_detection():
    """Test adapter detection and selection."""
    print("Testing Adapter Detection...")
    
    registry = AdapterRegistry()
    
    # Register adapters
    registry.register_adapter(MockAdapter())
    registry.register_adapter(MockCodeAdapter())
    
    # Test HTML adapter selection
    html_adapter = await registry.get_best_adapter("https://test.com/page")
    assert html_adapter is not None
    assert html_adapter.adapter_type == AdapterType.HTML
    
    # Test code adapter selection
    code_adapter = await registry.get_best_adapter("https://github.com/user/repo")
    assert code_adapter is not None
    assert code_adapter.adapter_type == AdapterType.CODE_REPO
    
    # Test no suitable adapter
    no_adapter = await registry.get_best_adapter("https://unknown.com/page")
    assert no_adapter is None
    
    print("Adapter detection working correctly")


async def test_content_extraction():
    """Test content extraction functionality."""
    print("Testing Content Extraction...")
    
    adapter = MockAdapter()
    
    # Test section extraction
    result = await adapter.extract_content(
        url="https://test.com/page",
        capabilities=[Capability.SECTION]
    )
    
    assert len(result.content_blocks) == 1
    assert result.content_blocks[0].content_type == ContentType.SECTION
    assert result.adapter_used == AdapterType.HTML
    assert Capability.SECTION in result.capabilities_provided
    
    # Test multiple capability extraction
    result = await adapter.extract_content(
        url="https://test.com/page",
        capabilities=[Capability.SECTION, Capability.NAV_GRAPH]
    )
    
    assert len(result.content_blocks) == 2
    content_types = {block.content_type for block in result.content_blocks}
    assert ContentType.SECTION in content_types
    assert ContentType.NAV_BAR in content_types
    
    print("Content extraction working correctly")


async def test_robots_txt_checking():
    """Test robots.txt checking functionality."""
    print("Testing Robots.txt Checking...")
    
    adapter = MockAdapter()
    
    # Mock robots.txt response
    with patch('adapters.base.RobotFileParser') as mock_robot_parser:
        mock_parser_instance = Mock()
        mock_parser_instance.can_fetch.return_value = True
        mock_robot_parser.return_value = mock_parser_instance
        
        # Test robots.txt allowed
        allowed = await adapter.check_robots_txt("https://example.com/page")
        assert allowed == True
        
        # Test robots.txt disallowed
        mock_parser_instance.can_fetch.return_value = False
        disallowed = await adapter.check_robots_txt("https://example.com/page")
        assert disallowed == False
    
    print("Robots.txt checking working correctly")


async def test_url_validation():
    """Test URL validation functionality."""
    print("Testing URL Validation...")
    
    adapter = MockAdapter()
    
    # Test valid URL
    with patch('httpx.AsyncClient') as mock_client:
        mock_response = Mock()
        mock_response.status_code = 200
        mock_client.return_value.__aenter__.return_value.head.return_value = mock_response
        
        valid = await adapter.validate_url("https://example.com")
        assert valid == True
    
    # Test invalid URL
    with patch('httpx.AsyncClient') as mock_client:
        mock_client.return_value.__aenter__.return_value.head.side_effect = Exception("Connection failed")
        
        invalid = await adapter.validate_url("https://invalid-url")
        assert invalid == False
    
    print("URL validation working correctly")


async def test_link_extraction():
    """Test link extraction from HTML content."""
    print("Testing Link Extraction...")
    
    adapter = MockAdapter()
    
    html_content = '''
    <html>
        <body>
            <a href="/page1">Page 1</a>
            <a href="https://external.com">External</a>
            <a href="#anchor">Anchor</a>
            <a href="mailto:test@example.com">Email</a>
        </body>
    </html>
    '''
    
    links = await adapter.extract_links(html_content, "https://example.com")
    
    assert len(links) == 3  # HTTP/HTTPS links including converted anchors
    assert "https://example.com/page1" in links
    assert "https://external.com" in links
    assert "https://example.com#anchor" in links
    
    print("Link extraction working correctly")


async def test_global_registry_functions():
    """Test global registry convenience functions."""
    print("Testing Global Registry Functions...")
    
    # Clear any existing adapters
    from adapters.base import adapter_registry
    adapter_registry._adapters.clear()
    
    # Test registration
    adapter = MockAdapter()
    register_adapter(adapter)
    
    assert len(adapter_registry.list_adapters()) == 1
    assert AdapterType.HTML in adapter_registry.list_adapters()
    
    # Test getting best adapter
    best_adapter = await get_best_adapter("https://test.com/page")
    assert best_adapter is not None
    assert best_adapter.adapter_type == AdapterType.HTML
    
    print("Global registry functions working correctly")


async def main():
    """Run all base adapter tests."""
    print("Testing WebCrawlApp Base Adapter Infrastructure...")
    print("=" * 60)
    
    try:
        test_base_adapter_initialization()
        test_content_quality_scoring()
        test_content_block_creation()
        test_capability_mapping()
        test_adapter_registry()
        await test_adapter_detection()
        await test_content_extraction()
        await test_robots_txt_checking()
        await test_url_validation()
        await test_link_extraction()
        await test_global_registry_functions()
        
        print("=" * 60)
        print("All base adapter tests passed successfully!")
        print("The base adapter infrastructure is working correctly.")
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
