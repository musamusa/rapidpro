from django.urls import reverse

from temba.tests import TembaTest

from ...models import Channel


class CCLTestChannelTypeTest(TembaTest):
    def test_claim(self):
        Channel.objects.all().delete()

        url = reverse("channels.types.ccl_test_channel.claim")
        self.login(self.admin)

        self.org.timezone = "Africa/Lagos"
        self.org.save()

        # check that claim page URL appears on claim list page
        response = self.client.get(reverse("channels.channel_claim"))
        self.assertContains(response, url)
        # visit the CCL Test Channel page
        response = self.client.get(url)
        self.assertEqual(200, response.status_code)
        post_data = response.context["form"].initial

        post_data["shortcode"] = "30303"
        post_data["username"] = "temba"
        post_data["api_key"] = "asdf-asdf-asdf-asdf-asdf"
        post_data["country"] = "NG"

        response = self.client.post(url, post_data)

        channel = Channel.objects.get()

        self.assertEqual("temba", channel.config["username"])
        self.assertEqual("asdf-asdf-asdf-asdf-asdf", channel.config["api_key"])
        self.assertEqual("30303", channel.address)
        self.assertEqual("NG", channel.country)
        self.assertEqual("CCL", channel.channel_type)

        config_url = reverse("channels.channel_configuration", args=[channel.uuid])
        self.assertRedirect(response, config_url)

        response = self.client.get(config_url)
        self.assertEqual(200, response.status_code)

        self.assertContains(response, reverse("courier.ccl", args=[channel.uuid, "receive"]))
        self.assertContains(response, reverse("courier.ccl", args=[channel.uuid, "status"]))
